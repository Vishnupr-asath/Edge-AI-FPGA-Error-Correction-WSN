`timescale 1ns / 1ps

module hamming_decoder(
    input [6:0] code_in,      // Input {d3, d2, d1, p2, d0, p1, p0}
    output [3:0] data_out,
    output error_detected
);

    wire s0, s1, s2; // Syndrome bits
    reg [6:0] corrected_code;
    
    // Extract data and parity bits from input
    wire d3, d2, d1, d0, p2, p1, p0;
    assign {d3, d2, d1, p2, d0, p1, p0} = code_in;

    // Standard syndrome calculation
    assign s0 = p0 ^ d0 ^ d1 ^ d3;
    assign s1 = p1 ^ d0 ^ d2 ^ d3;
    assign s2 = p2 ^ d1 ^ d2 ^ d3;

    assign error_detected = (s0 | s1 | s2);

    always @(*) begin
        corrected_code = code_in; 
        if (error_detected) begin
            case ({s2, s1, s0})
                3'b001: corrected_code[0] = ~corrected_code[0]; // Flip pos1 (bit 0)
                3'b010: corrected_code[1] = ~corrected_code[1]; // Flip pos2 (bit 1)
                3'b011: corrected_code[2] = ~corrected_code[2]; // Flip pos3 (bit 2, d0)
                3'b100: corrected_code[3] = ~corrected_code[3]; // Flip pos4 (bit 3, p2)
                3'b101: corrected_code[4] = ~corrected_code[4]; // Flip pos5 (bit 4, d1)
                3'b110: corrected_code[5] = ~corrected_code[5]; // Flip pos6 (bit 5, d2)
                3'b111: corrected_code[6] = ~corrected_code[6]; // Flip pos7 (bit 6, d3)
                default: corrected_code = code_in;
            endcase
        end
    end

    // Extract the corrected data bits {d3, d2, d1, d0}
    assign data_out = {corrected_code[6], corrected_code[5], corrected_code[4], corrected_code[2]};

endmodule