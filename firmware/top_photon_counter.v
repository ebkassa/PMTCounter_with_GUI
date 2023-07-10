`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 12/08/2022 10:31:44 AM
// Design Name: 
// Module Name: top_photon_counter
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


module top_photon_counter #(parameter ADDRSIZE = 10, DATASIZE = 16, COUNTSIZE = 32)
(
  input  [4:0]  okUH,
  output [3:0]  okHU,
  input  [3:0]  okRSVD,
  inout  [31:0] okUHU,
  inout         okAA,
  input         c_ch1,
  input         sys_clkp,
  input         sys_clkn,
  output        lockin_inc
    );
    
// Target Interface Bus 
wire [112:0] okHE;
wire [64:0]  okEH;
wire [31:0]  ep00wire, ep01wire, ep02wire, ep03wire, ep04wire, ep20wire, ep21wire;
wire [31:0]  ep05wire, ep06wire, ep07wire, ep08wire;

// Clock 
wire sys_clk, c_clk, g_clk;
IBUFGDS osc_clk(.O(sys_clk), .I(sys_clkp), .IB(sys_clkn));
clk_wiz_460mhz clk_wiz_460mhz(.clk_460MHz(c_clk), .clk_in1(sys_clk));

// Reset
wire c_rst, g_rst, g_rst_fifo, m_rst;
assign g_rst = ep00wire[0]; //Reset signal received from PC
assign c_rst = g_rst;
assign g_rst_fifo = ep00wire[1]; //FIFO reset signal receive from PC. After FIFO reset, waiting for 30 clcoks to allow asserting WE/RE signals. On PC, first reset FIFO, then wait 0.001 s, then reset.
assign m_rst = ep00wire[2]; //Reset for MUX to output TTL.

// Photon Counter 
wire [ 2*COUNTSIZE-1 : 0 ] c_ch1_cnt_output;
wire c_cnt_ready, c_lockin_inc;
reg [ COUNTSIZE-1 : 0 ]  c_count_period, c_lockinup_period, c_lockindown_period;
reg [ 6 : 0 ]  c_lockinup_rate, c_lockindown_rate; //the rates are in range 1~99. 7 bit is enough. 
reg  c_lockin, c_lockin_compensate;
//assign c_count_period = ep01wire; // counting period received from PC 
//assign c_lockin = ep02wire[0]; // lock-in flag received from PC 
//assign c_lockinup_period = ep03wire; // lockin length for counting up (received from PC)
//assign c_lockindown_period = ep04wire; // lockin length for counting down (received from PC)
always @(posedge c_rst) begin
  c_count_period <= ep01wire; // counting period received from PC 
  c_lockin <= ep02wire[0]; // lock-in flag received from PC 
  c_lockinup_period <= ep03wire; // lockin length for counting up (received from PC)
  c_lockindown_period <= ep04wire; // lockin length for counting down (received from PC)
  c_lockinup_rate <= ep05wire[6:0];
  c_lockindown_rate <= ep06wire[6:0];
  c_lockin_compensate <= ep07wire[0];
end 

// for debug
//localparam LOCKIN_PERIOD = 4600000;
//assign c_lockinup_period = LOCKIN_PERIOD; // lockin length for counting up (received from PC)
//assign c_lockindown_period = LOCKIN_PERIOD; // lockin length for counting down (received from PC)
wire lockin_inc_tmp;
photon_cnt_output #(COUNTSIZE) photon_cnt_output(.c_rst(c_rst), .c_clk(c_clk), .c_lockin(c_lockin),
  .c_lockinup_period(c_lockinup_period), .c_lockindown_period(c_lockindown_period), .c_count_period(c_count_period), .c_ch1(c_ch1),
  .c_cnt_ready(c_cnt_ready), .c_ch1_cnt_output(c_ch1_cnt_output), .c_lockin_inc(lockin_inc_tmp),
  .c_lockinup_rate(c_lockinup_rate), .c_lockindown_rate(c_lockindown_rate), .c_lockin_compensate(c_lockin_compensate));

// Output TTL type 
reg [1:0] c_TTL_type;
always @(posedge m_rst) begin
  c_TTL_type <= ep08wire[1:0];
end 
assign lockin_inc = c_TTL_type == 0 ? 1 : (c_TTL_type == 2 ? 0 : lockin_inc_tmp);

// CDC 
wire c_cnt_ready_c2g, g_cnt_ready;
wire [ 2*COUNTSIZE-1 : 0 ]  c_ch1_cnt_output_c2g, g_sync2_ch1_cnt_output;
cdc_c2g #(DATASIZE, COUNTSIZE) cdc_c2g(.c_clk(c_clk), .c_rst(c_rst),  
    .c_detect(c_cnt_ready), .c_diff_count(c_ch1_cnt_output),
    .c_detect_c2g(c_cnt_ready_c2g), .c_diff_count_c2g(c_ch1_cnt_output_c2g));
cdc_g2ram #(DATASIZE, COUNTSIZE) cdc_g2ram(.g_clk(g_clk), .g_rst(g_rst), 
    .c_detect_c2g(c_cnt_ready_c2g), .c_diff_count_c2g(c_ch1_cnt_output_c2g),
    .g_valid(g_cnt_ready), .g_sync2_diff_count(g_sync2_ch1_cnt_output));

// FIFO 
wire g_fifofull, g_fifoempty, g_good_to_wr, g_good_to_rd;
wire [12:0] g_fifodatacount_w, g_fifodatacount_r;
wire [ COUNTSIZE-1 : 0 ] g_fifo_out;
//assign g_good_to_wr = (g_fifodatacount < 8192-1028); // HARD CODING 
assign g_good_to_wr = (g_fifodatacount_w < 8192-8); // HARD CODING 
//assign g_good_to_rd = (g_fifodatacount > 1028); // HARD CODING 
assign g_good_to_rd = (g_fifodatacount_r > 16); // HARD CODING 
reg g_wren; // For FIFO write 
reg g_pipeO_ready; // For FIFO read 
reg [ 2*COUNTSIZE-1 : 0 ] g_reg_fifo_in;
always @ (posedge g_clk, posedge g_rst_fifo) begin
  if (g_rst_fifo) begin
    g_wren <= 0;
    g_pipeO_ready <= 0;
  end
  else begin
    if (g_cnt_ready && g_good_to_wr) begin
      g_wren <= 1;
      g_reg_fifo_in <= g_sync2_ch1_cnt_output; // data to be written into FIFO
    end 
    else g_wren <= 0;
    
    if (g_good_to_rd) g_pipeO_ready <= 1;
    else g_pipeO_ready <= 0;
  end 
end 

//wire g_piperead;
fifo_generator_0 fifo(.clk(g_clk), .srst(g_rst_fifo), 
    .din(g_reg_fifo_in), .wr_en(g_wren), .rd_en(g_piperead), .dout(g_fifo_out),
    .full(g_fifofull), .empty(g_fifoempty), .wr_data_count(g_fifodatacount), .rd_data_count(g_fifodatacount_r));
    
// okHost  
okHost okHI(.okUH(okUH), .okHU(okHU), .okUHU(okUHU),
    .okRSVD(okRSVD), .okAA(okAA), .okClk(g_clk), 
    .okHE(okHE), .okEH(okEH));

wire [65*6-1:0] okEHx;
okWireOR # (.N(6)) wireOR(okEH, okEHx);

okWireIn wi00(.okHE(okHE), .ep_addr(8'h00), .ep_dataout(ep00wire));
okWireIn wi01(.okHE(okHE), .ep_addr(8'h01), .ep_dataout(ep01wire));
okWireIn wi02(.okHE(okHE), .ep_addr(8'h02), .ep_dataout(ep02wire));
okWireIn wi03(.okHE(okHE), .ep_addr(8'h03), .ep_dataout(ep03wire));
okWireIn wi04(.okHE(okHE), .ep_addr(8'h04), .ep_dataout(ep04wire));
okWireIn wi05(.okHE(okHE), .ep_addr(8'h05), .ep_dataout(ep05wire));
okWireIn wi06(.okHE(okHE), .ep_addr(8'h06), .ep_dataout(ep06wire));
okWireIn wi07(.okHE(okHE), .ep_addr(8'h07), .ep_dataout(ep07wire));
okWireIn wi08(.okHE(okHE), .ep_addr(8'h08), .ep_dataout(ep08wire));

okWireOut wo20(.okHE(okHE), .okEH(okEHx[ 0*65 +: 65 ]), .ep_addr(8'h20), .ep_datain(ep20wire));
okBTPipeOut poA1(.okHE(okHE), .okEH(okEHx[ 5*65 +: 65 ]), .ep_addr(8'ha0), .ep_read(g_piperead), 
       .ep_blockstrobe(), .ep_datain(g_fifo_out), .ep_ready(g_pipeO_ready));   

endmodule
