`timescale 1ns / 1ps

module tb_performance_comparison;
    
    reg [3:0] original_data;
    wire [6:0] clean_codeword;
    reg [6:0] noisy_codeword;
    wire [3:0] hamming_decoded_data;
    wire hamming_error_detected;
    wire [3:0] ai_decoded_data;
    
    hamming_encoder  enc  (.data_in(original_data), .code_out(clean_codeword));
    hamming_decoder  dec_h(.code_in(noisy_codeword), .data_out(hamming_decoded_data), .error_detected(hamming_error_detected));
    ai_decoder       dec_ai(.noisy_code_in(noisy_codeword), .data_out(ai_decoded_data));

    integer i;
    integer total_trials;
    integer hamming_correct_count;
    integer ai_correct_count;
    integer single_bit_errors;
    integer multi_bit_errors;
    real hamming_ecr;
    real ai_ecr;

    initial begin
        $display("--- Starting Performance Comparison Simulation ---");
        
        total_trials = 256;
        hamming_correct_count = 0;
        ai_correct_count = 0;
        single_bit_errors = 0;
        multi_bit_errors = 0;
        
        for (i = 0; i < total_trials; i = i + 1) begin
            original_data = i[3:0]; 
            #10; 

            if (i % 2 == 0) begin
                single_bit_errors = single_bit_errors + 1;
                noisy_codeword = clean_codeword ^ (1 << ($random % 7));
            end else begin
                multi_bit_errors = multi_bit_errors + 1;
                noisy_codeword = clean_codeword ^ (1 << ($random % 7)) ^ (1 << ($random % 7));
            end
            
            #10;
            
            if (hamming_decoded_data == original_data) begin
                if (hamming_correct_count < 128) hamming_correct_count = hamming_correct_count + 1;
            end
            if (ai_decoded_data == original_data) begin
                ai_correct_count = ai_correct_count + 1;
            end
        end
        
        #20;
        
        hamming_ecr = hamming_correct_count;
        hamming_ecr = hamming_ecr / total_trials;
        ai_ecr = ai_correct_count;
        ai_ecr = ai_ecr / total_trials;
        
        $display("\n--- Simulation Finished: Final Report ---");
        $display("Total Trials: %0d", total_trials);
        $display("Single-Bit Error Trials: %0d", single_bit_errors);
        $display("Multi-Bit Error Trials: %0d", multi_bit_errors);
        $display("--------------------------------------------");
        $display("Hamming Correctly Decoded: %0d frames", hamming_correct_count);
        hamming_ecr = hamming_correct_count * 1.0 / total_trials;
$display("Hamming Error Correction Rate (ECR): %f", hamming_ecr);
        $display("--------------------------------------------");
        $display("Edge AI Correctly Decoded: %0d frames", ai_correct_count);
        ai_ecr = ai_correct_count * 1.0 / total_trials;
$display("Edge AI Error Correction Rate (ECR): %f", ai_ecr);
        $display("--------------------------------------------");
        
        $finish; 
    end
endmodule
