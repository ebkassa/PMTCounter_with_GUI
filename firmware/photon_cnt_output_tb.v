`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 12/14/2022 10:41:20 AM
// Design Name: 
// Module Name: photon_cnt_output_tb
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module photon_cnt_output_tb #(parameter DATASIZE = 16, COUNTSIZE = 32)
(
    );
    
reg ch1, clk, rst, clk2;
wire [ COUNTSIZE-1 : 0 ] g_sync2_diff_count, c_lockinup_period, c_lockindown_period, c_count_period;
wire g_vlid, c_lockin, lockin_inc;  
wire c_cnt_ready; 
wire [ COUNTSIZE-1 : 0 ] c_ch1_cnt_output;
assign  c_lockin = 0;
assign  lockin_inc = 1;
assign  c_lockinup_period = 128;
assign  c_lockindown_period = 128;
assign  c_count_period = 64;


photon_cnt_output #(COUNTSIZE) uut1(.c_rst(rst), .c_clk(clk), .c_lockin(c_lockin),
  .c_lockinup_period(c_lockinup_period), .c_lockindown_period(c_lockindown_period), .c_count_period(c_count_period), .c_ch1(ch1),
  .c_cnt_ready(c_cnt_ready), .c_ch1_cnt_output(c_ch1_cnt_output), .c_lockin_inc(lockin_inc));

wire c_cnt_ready_c2g, g_cnt_ready;
wire [ COUNTSIZE-1 : 0 ]  c_ch1_cnt_output_c2g, g_sync2_ch1_cnt_output;
cdc_c2g #(DATASIZE, COUNTSIZE) cdc_c2g(.c_clk(clk), .c_rst(rst),  
    .c_detect(c_cnt_ready), .c_diff_count(c_ch1_cnt_output),
    .c_detect_c2g(c_cnt_ready_c2g), .c_diff_count_c2g(c_ch1_cnt_output_c2g));
cdc_g2ram #(DATASIZE, COUNTSIZE) cdc_g2ram(.g_clk(clk2), .g_rst(rst), 
    .c_detect_c2g(c_cnt_ready_c2g), .c_diff_count_c2g(c_ch1_cnt_output_c2g),
    .g_valid(g_cnt_ready), .g_sync2_diff_count(g_sync2_ch1_cnt_output));


initial begin
  clk = 0;
  clk2 = 0;
  rst = 0;
  ch1 = 0;
  fork 

    #15 ch1 = 1;
    #20 ch1 = 0;
    #30 ch1 = 1;
    #45 ch1 =0;
    #55 ch1 = 1;
    #60 ch1 =0;
    #2 rst = 1;
    #6 rst = 0;

    #155 ch1 = 1;
    #162 ch1 = 0;
    #280 ch1 = 1;
    #300 ch1 = 0;
    #360 ch1 = 1;
    #370 ch1 = 0;
    #410 ch1 = 1;
    #447 ch1 = 0;  
  join
end 

always #2 clk = ~clk;
always #9 clk2 = ~clk2;
endmodule
