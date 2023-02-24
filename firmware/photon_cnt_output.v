`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 12/07/2022 04:16:03 PM
// Design Name: 
// Module Name: photon_cnt_output
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: It initiates "photon_counter" to count the pulses, sends c_cnt_ready signal and count value periodically (c_count_period) to FIFO.         
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module photon_cnt_output#(parameter COUNTSIZE = 32)
(
  input c_rst,
  input c_clk,
  input c_lockin,
  input [ COUNTSIZE-1 : 0 ] c_lockinup_period,
  input [ COUNTSIZE-1 : 0 ] c_lockindown_period,
  input [ COUNTSIZE-1 : 0 ] c_count_period,
  input [ 6 : 0 ] c_lockinup_rate,
  input [ 6 : 0 ] c_lockindown_rate,
  input c_lockin_compensate,
  input c_ch1,
  output reg c_cnt_ready,
  output reg[ COUNTSIZE-1 : 0 ] c_ch1_cnt_output,
  output wire c_lockin_inc // flag: increase or decrease the counter.
    );
    
reg [ COUNTSIZE-1 : 0 ] c_clk_cnt;
wire [ COUNTSIZE-1 : 0 ] c_ch1_cnt;

photon_counter #(COUNTSIZE) photon_counter(.c_rst(c_rst), .c_clk(c_clk), .c_lockin(c_lockin),
    .c_lockinup_period(c_lockinup_period), .c_lockindown_period(c_lockindown_period), 
    .c_ch1(c_ch1), .c_ch1_cnt(c_ch1_cnt), .c_lockin_inc(c_lockin_inc),
    .c_lockinup_rate(c_lockinup_rate), .c_lockindown_rate(c_lockindown_rate), .c_lockin_compensate(c_lockin_compensate));
    
always @ (posedge c_rst, posedge c_clk) begin
  if (c_rst) begin
    c_clk_cnt <= 0;
    c_ch1_cnt_output <= 0;
    c_cnt_ready <= 0;
  end
  else begin
    c_clk_cnt <= c_clk_cnt + 1;
    if (c_clk_cnt == c_count_period) begin 
      c_ch1_cnt_output <= c_ch1_cnt;
      c_cnt_ready <= 1;
      c_clk_cnt <= 1;  //start next counting period.
    end 
    if (c_cnt_ready) c_cnt_ready <= 0; // only keep ready signal for one clock.
  end 
end 



    
endmodule
