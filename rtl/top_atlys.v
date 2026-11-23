// top_atlys.v  (Spartan-6 / Atlys demo wrapper)
// SW[3:0]  = original 4-bit data (d3..d0)
// SW[6:0]  = error mask for codeword bits (p0..p2,d0,d1,d2,d3) order shown below
// SW[7]    = display select (0 = status/data, 1 = show noisy codeword)
// BTN[0]   = reset (active-high)
// LED[7:0] = see mapping at bottom

module top_atlys(
    input  wire        clk100,     // 100 MHz Atlys system clock
    input  wire [7:0]  sw,         // slide switches
    input  wire [4:0]  btn,        // push buttons (btn[0] used as reset)
    output wire [7:0]  led         // user LEDs
);
    // ---------------- Reset (sync) ----------------
    reg [3:0] rst_sr;
    always @(posedge clk100 or posedge btn[0]) begin
        if (btn[0]) rst_sr <= 4'b1111;
        else        rst_sr <= {rst_sr[2:0], 1'b0};
    end
    wire reset = rst_sr[3];

    // ---------------- Original data ----------------
    // sw[3:0] == {d3,d2,d1,d0}
    wire [3:0] original_data = sw[3:0];

    // ---------------- Encode to (7,4) Hamming ----------------
    wire [6:0] clean_codeword;  // {d3,d2,d1,p2,d0,p1,p0}
    hamming_encoder enc (
        .data_in (original_data),
        .code_out(clean_codeword)
    );

    // ---------------- Error injection ----------------
    // sw[6:0] maps to code bits {p0,p1,d0,p2,d1,d2,d3} *from LSB to MSB* as below:
    // We want mask in the SAME bit order as the codeword: {d3,d2,d1,p2,d0,p1,p0}.
    // So we reorder the switch mask accordingly.
    wire [6:0] sw_mask_reordered = {
        sw[6], // d3
        sw[5], // d2
        sw[4], // d1
        sw[3], // p2  (note: sw[3] is also d1 above; don't confuse with original_data)
        sw[2], // d0
        sw[1], // p1
        sw[0]  // p0
    };

    wire [6:0] noisy_codeword = clean_codeword ^ sw_mask_reordered;

    // ---------------- Decoders ----------------
    wire [3:0] ham_data;
    wire       ham_err;  // not used for LEDs, but available

    hamming_decoder dec_h (
        .code_in       (noisy_codeword),
        .data_out      (ham_data),
        .error_detected(ham_err)
    );

    wire [3:0] ai_data;
    ai_decoder dec_ai (
        .noisy_code_in (noisy_codeword),
        .data_out      (ai_data)    // your latest ML(+AI) version drives this
    );

    // ---------------- Status flags ----------------
    wire ai_ok  = (ai_data  == original_data);
    wire ham_ok = (ham_data == original_data);

    // Optional: show the 7-bit codeword on LEDs across two pages
    // Page 0 (sw[7]=0): status + data
    // Page 1 (sw[7]=1): raw noisy codeword bits {d3,d2,d1,p2,d0,p1,p0,0}
    wire [7:0] page0 = {
        ai_ok,          // LED7: AI correct?
        ham_ok,         // LED6: Hamming correct?
        ai_data[3:2],   // LED5..4: AI d3..d2
        ai_data[1:0],   // LED3..2: AI d1..d0
        original_data[1:0] // LED1..0: original d1..d0 (quick compare)
    };

    wire [7:0] page1 = {
        noisy_codeword[6], // LED7: d3
        noisy_codeword[5], // LED6: d2
        noisy_codeword[4], // LED5: d1
        noisy_codeword[3], // LED4: p2
        noisy_codeword[2], // LED3: d0
        noisy_codeword[1], // LED2: p1
        noisy_codeword[0], // LED1: p0
        1'b0               // LED0: unused
    };

    assign led = sw[7] ? page1 : page0;

endmodule
