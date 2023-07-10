`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 11/24/2022 10:43:50 AM
// Design Name: 
// Module Name: photon_counter
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description:   The module counts the pulses in channel "c_ch1". 
//                If c_lockin, the counter toggles between increase and decrease in the period "c_lockinup_period" (in the unit of clocks of c_clk).
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module photon_counter #(parameter COUNTSIZE = 32)
(
  input c_rst,
  input c_clk,
  input c_lockin,
  input [ COUNTSIZE-1 : 0 ] c_lockinup_period,
  input [ COUNTSIZE-1 : 0 ] c_lockindown_period,
  input [ 6 : 0 ] c_lockinup_rate,
  input [ 6 : 0 ] c_lockindown_rate,
  input c_lockin_compensate,
  input c_ch1,
  output reg[ COUNTSIZE-1 : 0 ] c_ch1_cnt,
  output reg[ COUNTSIZE-1 : 0 ] c_ch1_cnt_lck,
  output reg c_lockin_inc // flag: increase or decrease the counter.
    );

wire [6:0] up_inc, down_inc;
assign up_inc = c_lockin_compensate == 1 ? c_lockindown_rate : 1;
assign down_inc = c_lockin_compensate == 1 ? c_lockinup_rate : 1;

wire c_ch_pos_edge;
edge_detect edge_detect(.clk(c_clk), .trig(c_ch1), .pos_edge(c_ch1_pos_edge), .neg_edge());

reg [ COUNTSIZE-1 : 0 ] c_clk_cnt;
always @ (posedge c_rst, posedge c_clk) begin
  if (c_rst) begin
    c_ch1_cnt <= 0;
    c_ch1_cnt_lck <= 0;
    c_clk_cnt <= 0;
    c_lockin_inc <= 1;
  end
  else begin
    //Create the flag c_lockin_inc: 1 for increase counting, 0 for decreass counting
    c_clk_cnt <= c_clk_cnt + 1;
    if (c_lockin_inc == 1 && c_clk_cnt == c_lockinup_period) begin //toggle from increase to decrese.
      c_clk_cnt <= 1; //start next lock-in period
      c_lockin_inc <= 0;
    end
    else if (c_lockin_inc == 0 && c_clk_cnt == c_lockindown_period) begin //toggle from decrese to increase.
      c_clk_cnt <= 1; //start next lock-in period
      c_lockin_inc <= 1;
    end
    
    // counting
    if (c_ch1_pos_edge) begin
      //normal counting
      c_ch1_cnt <= c_ch1_cnt + 1; 
      //lock-in counting 
      if(c_lockin_inc == 1) c_ch1_cnt_lck <= c_ch1_cnt_lck + up_inc;
      else c_ch1_cnt_lck <= c_ch1_cnt_lck - down_inc;   
    end    
  end 
end 
endmodule
