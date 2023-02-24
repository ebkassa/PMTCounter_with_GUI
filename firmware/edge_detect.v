`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 11/16/2022 03:38:42 PM
// Design Name: 
// Module Name: edge_detect
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
//   Detect the edges of a pulse signal, usually used as a triggering signal.
//   Output pos_edge and neg_edge, synchonized with the clock.
//   This module will run in counting clock domain (460MHz), using c_ prefix.
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module edge_detect(
  input clk,
  input trig,
  output pos_edge,
  output neg_edge
    );
  
  reg trig1, trig2;
  always @(posedge clk) {trig1, trig2} <= {trig, trig1};
  assign pos_edge = trig1 & ~trig2;
  assign neg_edge = ~trig1 & trig2;
  
endmodule
