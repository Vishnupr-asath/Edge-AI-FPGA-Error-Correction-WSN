import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

# ----------------------------
# 1. Hamming(7,4) encoder
# ----------------------------
def hamming74_encode(data4):
    d0, d1, d2, d3 = data4
    p1 = d0 ^ d1 ^ d3
    p2 = d0 ^ d2 ^ d3
    p3 = d1 ^ d2 ^ d3
    return np.array([p1, p2, d0, p3, d1, d2, d3], dtype=np.float32)

# ----------------------------
# 2. Dataset Generation
# ----------------------------
X = []
Y = []
for d in range(16):  # all 4-bit inputs
    data_bits = [(d>>i)&1 for i in range(4)]
    codeword = hamming74_encode(data_bits)
    for _ in range(50):  # noisy versions
        noisy = codeword.copy()
        num_err = np.random.choice([0,1,2], p=[0.6,0.3,0.1])
        flip_idx = np.random.choice(7, size=num_err, replace=False)
        for f in flip_idx:
            noisy[f] = 1 - noisy[f]
        X.append(noisy)
        Y.append(data_bits)

X = np.array(X)
Y = np.array(Y)

# ----------------------------
# 3. Tiny Neural Net
# ----------------------------
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

net = EdgeAIDecoder()
criterion = nn.BCELoss()
optimizer = optim.Adam(net.parameters(), lr=0.01)

# ----------------------------
# 4. Training
# ----------------------------
X_tensor = torch.tensor(X, dtype=torch.float32)
Y_tensor = torch.tensor(Y, dtype=torch.float32)

for epoch in range(200):
    optimizer.zero_grad()
    outputs = net(X_tensor)
    loss = criterion(outputs, Y_tensor)
    loss.backward()
    optimizer.step()
    if epoch % 50 == 0:
        print(f"Epoch {epoch}, Loss={loss.item():.4f}")

# ----------------------------
# 5. Export to Verilog arrays
# ----------------------------
def verilog_array(name, arr, signed=True):
    """Format numpy array as Verilog reg initialization"""
    lines = []
    dims = arr.shape
    for i in range(dims[0]):
        for j in range(dims[1]):
            val = int(np.round(arr[i,j]))
            lines.append(f"{name}[{i}][{j}] = {val};")
    return "\n".join(lines)

def verilog_bias(name, arr):
    lines = []
    for i,v in enumerate(arr):
        lines.append(f"{name}[{i}] = {int(np.round(v))};")
    return "\n".join(lines)

# Extract weights/biases
W_hidden = net.hidden.weight.detach().numpy()
b_hidden = net.hidden.bias.detach().numpy()
W_out = net.out.weight.detach().numpy()
b_out = net.out.bias.detach().numpy()

print("\n// ----- Verilog Code Snippet -----")
print("// Hidden layer weights")
print(verilog_array("W_hidden", W_hidden))
print("// Hidden layer bias")
print(verilog_bias("b_hidden", b_hidden))
print("// Output layer weights")
print(verilog_array("W_out", W_out))
print("// Output layer bias")
print(verilog_bias("b_out", b_out))
print("// ----- End Snippet -----")
