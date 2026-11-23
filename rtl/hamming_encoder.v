`timescale 1ns / 1ps

module hamming_encoder(
    input [3:0] data_in,    // Input data {d3, d2, d1, d0}
    output [6:0] code_out   // Output codeword {d3, d2, d1, p2, d0, p1, p0}
);

    wire p0, p1, p2;

    // Standard parity bit calculations for (7,4) Hamming
    assign p0 = data_in[0] ^ data_in[1] ^ data_in[3]; // d0 ^ d1 ^ d3
    assign p1 = data_in[0] ^ data_in[2] ^ data_in[3]; // d0 ^ d2 ^ d3
    assign p2 = data_in[1] ^ data_in[2] ^ data_in[3]; // d1 ^ d2 ^ d3

    // Assemble the codeword (systematic form)
    assign code_out = {data_in[3], data_in[2], data_in[1], p2, data_in[0], p1, p0};

endmodule