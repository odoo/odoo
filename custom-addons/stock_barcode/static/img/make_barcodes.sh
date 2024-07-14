#!/bin/sh

barcode -t 2x7+40+40 -m 50x30 -p "210x297mm" -e code128b -n > barcodes_actions_barcode.ps << BARCODES
O-CMD.MAIN-MENU
O-CMD.DISCARD
O-BTN.validate
O-CMD.cancel
O-BTN.print-op
O-BTN.print-slip
O-BTN.pack
O-BTN.scrap
O-BTN.record-components
O-CMD.PREV
O-CMD.NEXT
O-CMD.PAGER-FIRST
O-CMD.PAGER-LAST
O-BTN.return
BARCODES

cat > barcodes_actions_header.ps << HEADER
/showTitle { /Helvetica findfont 12 scalefont setfont moveto show } def
(MAIN MENU) 89 768 showTitle
(DISCARD) 348 768 showTitle
(VALIDATE) 89 660 showTitle
(CANCEL) 348 660 showTitle
(PRINT PICKING OPERATION) 89 551 showTitle
(PRINT DELIVERY SLIP) 348 551 showTitle
(PUT IN PACK) 89 444 showTitle
(SCRAP) 348 444 showTitle
(RECORD COMPONENTS) 89 337 showTitle
(PREVIOUS PAGE) 348 337 showTitle
(NEXT PAGE) 89 230 showTitle
(FIRST PAGE) 348 230 showTitle
(LAST PAGE) 89 123 showTitle
(RETURN) 348 123 showTitle

HEADER

cat barcodes_actions_header.ps barcodes_actions_barcode.ps | ps2pdf - - > barcodes_actions.pdf
rm barcodes_actions_header.ps barcodes_actions_barcode.ps

# pg 1 of demo barcodes due to ps headers being restricted to 1 page. Some blanks may exist due to flows having a rows with less than 3 barcodes.
barcode -t 3x7+20+35 -m 25x30 -p "210x297mm" -e code128b -n > barcodes_demo_barcode_pg_1.ps  << BARCODES
WH-RECEIPTS
601647855638
O-BTN.validate
WH/OUT/00005
601647855644
O-BTN.validate
WH-RECEIPTS
601647855640
601647855631
LOT-000002
LOT-000003
O-BTN.validate
WH-STOCK
601647855649
2601892
O-BTN.validate


WH-RECEIPTS
601647855650
O-BTN.pack
BARCODES

# blank lines included for easier visual matching to barcode spacing
cat > barcodes_demo_header_pg_1.ps << HEADER
/showLabel { /Helvetica findfont 14 scalefont setfont moveto show } def
/showTitle { /Helvetica findfont 11 scalefont setfont moveto show } def
/showCode { /Helvetica findfont 8 scalefont setfont moveto show } def
/showFooter { /Helvetica findfont 8 scalefont setfont moveto show } def
(Receive products in stock) 45 797 showLabel
(YourCompany Receipts) 45 777 showTitle
(WH-RECEIPTS) 85 718 showCode
(Desk Stand with Screen) 230 777 showTitle
(601647855638) 271 718 showCode
(Validate) 415 777 showTitle
(O-BTN.validate) 456 718 showCode
(Deliver products to your customers) 45 687 showLabel
(WH/OUT/00005) 45 667 showTitle
(WH/OUT/00005) 85 608 showCode
(Desk Combination) 230 667 showTitle
(601647855644) 271 608 showCode
(Validate) 415 667 showTitle
(O-BTN.validate) 456 608 showCode
(Receive products tracked by lot number (activate Lots & Serial Numbers)) 45 577 showLabel
(YourCompany Receipts) 45 557 showTitle
(WH-RECEIPTS) 85 498 showCode
(Corner Desk Black) 230 557 showTitle
(601647855640) 271 498 showCode
(Cable Management Box) 415 557 showTitle
(601647855631) 456 498 showCode
(LOT-000002) 45 447 showTitle
(LOT-000002) 85 388 showCode
(LOT-000003) 230 447 showTitle
(LOT-000003) 271 388 showCode
(Validate) 415 447 showTitle
(O-BTN.validate) 456 388 showCode
(Internal transfer (activate Storage Locations)) 45 357 showLabel
(WH/Stock) 45 337 showTitle
(WH-STOCK) 85 278 showCode
(Pedal Bin) 230 337 showTitle
(601647855649) 271 278 showCode
(WH/Stock/Shelf1) 415 337 showTitle
(2601892) 456 278 showCode
(Validate) 45 227 showTitle
(O-BTN.validate) 85 168 showCode


(Put in Pack (activate Packages)) 45 137 showLabel
(YourCompany Receipts) 45 117 showTitle
(WH-RECEIPTS) 85 58 showCode
(Large Cabinet) 230 117 showTitle
(601647855650) 271 58 showCode
(Put in Pack) 415 117 showTitle
(O-BTN.pack) 456 58 showCode

(Don't have any barcode scanner? Right click on your screen > Inspect > Console and type the following command:) 45 35 showFooter
(   odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", {barcode:"setyourbarcodehere"})) 45 25 showFooter
(and replace "setyourbarcodehere" by the barcode you would like to scan OR use our mobile app.) 45 15 showFooter
HEADER

# pg 2 of demo barcodes. Some blanks may exist due to flows having a rows with less than 3 barcodes.
barcode -t 3x7+20+35 -m 25x30 -p "210x297mm" -e code128b -n > barcodes_demo_barcode_pg_2.ps  << BARCODES
O-BTN.validate


BATCH/00002
601647855637
601647855651
601647855635
O-BTN.validate

BATCH/00001
601647855652
CLUSTER-PACK-1
601647855653
CLUSTER-PACK-1
601647855651
CLUSTER-PACK-2
O-BTN.validate

BARCODES

cat > barcodes_demo_header_pg_2.ps << HEADER
/showLabel { /Helvetica findfont 14 scalefont setfont moveto show } def
/showTitle { /Helvetica findfont 11 scalefont setfont moveto show } def
/showCode { /Helvetica findfont 8 scalefont setfont moveto show } def
/showFooter { /Helvetica findfont 8 scalefont setfont moveto show } def
(Validate) 45 777 showTitle
(O-BTN.validate) 85 718 showCode


(Batch picking (activate Batch Pickings)) 45 687 showLabel
(BATCH/00002) 45 667 showTitle
(BATCH/00002) 85 608 showCode
(Large Meeting Table) 230 667 showTitle
(601647855637) 271 608 showCode
(Four Person Desk) 415 667 showTitle
(601647855651) 456 608 showCode
(Three-Seat Sofa) 45 557 showTitle
(601647855635) 85 498 showCode
(Validate) 230 557 showTitle
(O-BTN.validate) 271 498 showCode

(Batch picking with cluster pickings (activate Batch Pickings and Packages)) 45 467 showLabel
(BATCH/00001) 45 447 showTitle
(BATCH/00001) 85 388 showCode
(Cabinet with Doors) 230 447 showTitle
(601647855652) 271 388 showCode
(CLUSTER-PACK-1) 415 447 showTitle
(CLUSTER-PACK-1) 456 388 showCode
(Acoustic Bloc Screens) 45 337 showTitle
(601647855653) 85 278 showCode
(CLUSTER-PACK-1) 230 337 showTitle
(CLUSTER-PACK-1) 271 278 showCode
(Four Person Desk) 415 337 showTitle
(601647855651) 456 278 showCode
(CLUSTER-PACK-2) 45 227 showTitle
(CLUSTER-PACK-2) 85 168 showCode
(Validate) 230 227 showTitle
(O-BTN.validate) 271 168 showCode

(Don't have any barcode scanner? Right click on your screen > Inspect > Console and type the following command:) 45 35 showFooter
(   odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", {barcode:"setyourbarcodehere"})) 45 25 showFooter
(and replace "setyourbarcodehere" by the barcode you would like to scan OR use our mobile app.) 45 15 showFooter
HEADER

cat barcodes_demo_header_pg_1.ps barcodes_demo_barcode_pg_1.ps barcodes_demo_header_pg_2.ps barcodes_demo_barcode_pg_2.ps | ps2pdf - - > barcodes_demo.pdf
rm barcodes_demo_header_pg_1.ps barcodes_demo_barcode_pg_1.ps
rm barcodes_demo_header_pg_2.ps barcodes_demo_barcode_pg_2.ps

python3 make_barcodes.py
