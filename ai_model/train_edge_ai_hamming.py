import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

# =========================
# Reproducibility
# =========================
SEED = 1234
np.random.seed(SEED)
torch.manual_seed(SEED)

# =========================
# Hamming(7,4) encoder
# Mapping must match your Verilog:
# code_out = {d3, d2, d1, p3, d0, p2, p1} indexes [6..0]
# =========================
def hamming74_encode(d4):
    d0, d1, d2, d3 = d4
    p1 = d0 ^ d1 ^ d3
    p2 = d0 ^ d2 ^ d3
    p3 = d1 ^ d2 ^ d3
    return np.array([d3, d2, d1, p3, d0, p2, p1], dtype=np.float32)

# =========================
# Dataset generation
# p1: prob of single-bit flip
# p2: prob of double-bit flip
# n_per_symbol: samples per 4-bit value
# =========================
def make_dataset(n_per_symbol=400, p1=0.25, p2=0.10):
    X, Y, flips_list = [], [], []
    for d in range(16):
        data_bits = np.array([(d >> i) & 1 for i in range(4)], dtype=np.float32)
        code = hamming74_encode(data_bits)
        for _ in range(n_per_symbol):
            noisy = code.copy()
            r = np.random.rand()
            flips = 0
            if r < p2:
                # two flips
                b1, b2 = np.random.randint(0, 7), np.random.randint(0, 7)
                while b2 == b1:
                    b2 = np.random.randint(0, 7)
                noisy[b1] = 1.0 - noisy[b1]
                noisy[b2] = 1.0 - noisy[b2]
                flips = 2
            elif r < p2 + p1:
                b = np.random.randint(0, 7)
                noisy[b] = 1.0 - noisy[b]
                flips = 1
            else:
                flips = 0
            X.append(noisy)
            Y.append(data_bits)
            flips_list.append(flips)
    X = np.array(X, dtype=np.float32)
    Y = np.array(Y, dtype=np.float32)
    flips_list = np.array(flips_list, dtype=np.int32)
    return X, Y, flips_list

# =========================
# Model: tiny MLP 7 -> 4 -> 4
# =========================
class EdgeAIDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.hidden = nn.Linear(7, 4)
        self.out = nn.Linear(4, 4)
        self.act = nn.ReLU()
    def forward(self, x):
        x = self.act(self.hidden(x))
        x = torch.sigmoid(self.out(x))
        return x

# =========================
# Quantization to int8
# =========================
def quantize_int8(W: np.ndarray):
    max_abs = float(np.max(np.abs(W))) if np.max(np.abs(W)) > 0 else 1e-8
    s = max_abs / 127.0
    Wq = np.clip(np.round(W / s), -127, 127).astype(np.int8)
    return Wq, s

# =========================
# Evaluation helpers
# =========================
def to_bits(x, thr=0.5):
    return (x >= thr).astype(np.int32)

def eval_frame_ecr(model, X, Y, flips_vec):
    model.eval()
    with torch.no_grad():
        P = model(torch.tensor(X, dtype=torch.float32)).cpu().numpy()
    P_bits = to_bits(P, 0.5)
    Y_bits = Y.astype(np.int32)
    # frames with errors
    err_mask = flips_vec > 0
    total_err_frames = int(err_mask.sum())
    corrected_frames = int(((P_bits == Y_bits).all(axis=1) & err_mask).sum())
    ecr_frames = corrected_frames / total_err_frames if total_err_frames > 0 else 0.0
    # split by 1-bit and 2-bit frames
    mask1 = flips_vec == 1
    mask2 = flips_vec == 2
    total1 = int(mask1.sum())
    total2 = int(mask2.sum())
    corr1 = int(((P_bits == Y_bits).all(axis=1) & mask1).sum())
    corr2 = int(((P_bits == Y_bits).all(axis=1) & mask2).sum())
    ecr1 = corr1 / total1 if total1 > 0 else 0.0
    ecr2 = corr2 / total2 if total2 > 0 else 0.0
    bit_acc = float((P_bits == Y_bits).mean())
    return {
        "bit_accuracy": bit_acc,
        "ecr_frames_all": ecr_frames,
        "frames_err1": total1, "frames_err2": total2,
        "ecr_frames_1bit": ecr1,
        "ecr_frames_2bit": ecr2
    }

# =========================
# Export Verilog arrays
# Also write to edge_ai_weights.vh
# =========================
def export_verilog_arrays(Wh_q, bh_q, Wo_q, bo_q, fname="edge_ai_weights.vh"):
    lines = []
    lines.append("// Auto-generated NN weights for edge_ai_decoder.v")
    lines.append("// Paste these inside the 'initial begin' or `include this file`.\n")
    # Hidden
    lines.append("// Hidden layer weights (4x7)")
    for i in range(4):
        for j in range(7):
            lines.append(f"W_hidden[{i}][{j}] = {int(Wh_q[i,j])};")
    lines.append("// Hidden layer bias (4)")
    for i in range(4):
        lines.append(f"b_hidden[{i}] = {int(bh_q[i])};")
    # Output
    lines.append("// Output layer weights (4x4)")
    for i in range(4):
        for j in range(4):
            lines.append(f"W_out[{i}][{j}] = {int(Wo_q[i,j])};")
    lines.append("// Output layer bias (4)")
    for i in range(4):
        lines.append(f"b_out[{i}] = {int(bo_q[i])};")
    txt = "\n".join(lines)
    print("\n===== Verilog snippet (copy-paste) =====")
    print(txt)
    print("===== End snippet =====\n")
    with open(fname, "w") as f:
        f.write(txt)
    print(f"Saved Verilog weights to: {fname}")

# =========================
# Main
# =========================
if __name__ == "__main__":
    # 1) Generate dataset
    # Tune p1/p2 depending on what you want the NN to learn.
    X, Y, flips = make_dataset(n_per_symbol=400, p1=0.25, p2=0.12)

    # Split
    n = len(X)
    idx = np.random.permutation(n)
    tr = int(0.8 * n)
    Xtr, Ytr, Ftr = X[idx[:tr]], Y[idx[:tr]], flips[idx[:tr]]
    Xte, Yte, Fte = X[idx[tr:]], Y[idx[tr:]], flips[idx[tr:]]

    # 2) Build & train model (CPU)
    net = EdgeAIDecoder()
    crit = nn.BCELoss()
    opt = optim.Adam(net.parameters(), lr=1e-2)

    Xt = torch.tensor(Xtr, dtype=torch.float32)
    Yt = torch.tensor(Ytr, dtype=torch.float32)

    EPOCHS = 300
    for epoch in range(EPOCHS):
        opt.zero_grad()
        out = net(Xt)
        loss = crit(out, Yt)
        loss.backward()
        opt.step()
        if epoch % 50 == 0 or epoch == EPOCHS-1:
            print(f"Epoch {epoch:3d}  Loss={loss.item():.4f}")

    # 3) Evaluate (float model)
    stats = eval_frame_ecr(net, Xte, Yte, Fte)
    print("\n=== FLOAT model evaluation ===")
    print(f"Bit accuracy         : {stats['bit_accuracy']:.4f}")
    print(f"ECR (frames, all)    : {stats['ecr_frames_all']:.4f}")
    print(f"Frames 1-bit / 2-bit : {stats['frames_err1']} / {stats['frames_err2']}")
    print(f"ECR (1-bit frames)   : {stats['ecr_frames_1bit']:.4f}")
    print(f"ECR (2-bit frames)   : {stats['ecr_frames_2bit']:.4f}")

    # 4) Export INT8 weights
    Wh = net.hidden.weight.detach().numpy()   # (4,7)
    bh = net.hidden.bias.detach().numpy()     # (4,)
    Wo = net.out.weight.detach().numpy()      # (4,4)
    bo = net.out.bias.detach().numpy()        # (4,)

    Wh_q, sWh = quantize_int8(Wh)
    bh_q, sbh = quantize_int8(bh.reshape(-1,1)); bh_q = bh_q.flatten()
    Wo_q, sWo = quantize_int8(Wo)
    bo_q, sbo = quantize_int8(bo.reshape(-1,1)); bo_q = bo_q.flatten()

    print("\nQuant scales (for reference):")
    print(f" hidden W:{sWh:.6f}  hidden b:{sbh:.6f}  out W:{sWo:.6f}  out b:{sbo:.6f}")

    export_verilog_arrays(Wh_q.astype(int), bh_q.astype(int), Wo_q.astype(int), bo_q.astype(int))
