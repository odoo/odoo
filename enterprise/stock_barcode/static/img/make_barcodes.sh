#!/bin/sh

barcode -t 2x7+40+40 -m 50x30 -p "210x297mm" -e code128b -n > barcodes_actions_barcode.ps << BARCODES
OCDMENU
OCDDISC
OBTVALI
OCDCANC
OBTPROP
OBTPRSL
OBTPACK
OBTSCRA
OBTRECO
OBTRETU
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
(RETURN) 348 337 showTitle

HEADER

cat barcodes_actions_header.ps barcodes_actions_barcode.ps | ps2pdf - - > barcodes_actions.pdf
rm barcodes_actions_header.ps barcodes_actions_barcode.ps

# pg 1 of demo barcodes due to ps headers being restricted to 1 page. Some blanks may exist due to flows having a rows with less than 3 barcodes.
barcode -t 3x7+20+35 -m 25x30 -p "210x297mm" -e code128b -n > barcodes_demo_barcode_pg_1.ps  << BARCODES
WHIN
6016478556387
OBTVALI
WH/OUT/00005
6016478556448
OBTVALI
WHIN
6016478556400
6016478556318
LOT-000002
LOT-000003
OBTVALI
WHSTOCK
6016478556493
SHELF1
OBTVALI


WHIN
6016478556509
OBTPACK
BARCODES

# blank lines included for easier visual matching to barcode spacing
cat > barcodes_demo_header_pg_1.ps << HEADER
/showLabel { /Helvetica findfont 14 scalefont setfont moveto show } def
/showTitle { /Helvetica findfont 11 scalefont setfont moveto show } def
/showCode { /Helvetica findfont 8 scalefont setfont moveto show } def
/showFooter { /Helvetica findfont 8 scalefont setfont moveto show } def
(Receive products in stock) 45 797 showLabel
(YourCompany Receipts) 45 777 showTitle
(WHIN) 85 718 showCode
(Desk Stand with Screen) 230 777 showTitle
(6016478556387) 271 718 showCode
(Validate) 415 777 showTitle
(OBTVALI) 456 718 showCode
(Deliver products to your customers) 45 687 showLabel
(WH/OUT/00005) 45 667 showTitle
(WH/OUT/00005) 85 608 showCode
(Desk Combination) 230 667 showTitle
(6016478556448) 271 608 showCode
(Validate) 415 667 showTitle
(OBTVALI) 456 608 showCode
(Receive products tracked by lot number (activate Lots & Serial Numbers)) 45 577 showLabel
(YourCompany Receipts) 45 557 showTitle
(WHIN) 85 498 showCode
(Corner Desk Black) 230 557 showTitle
(6016478556400) 271 498 showCode
(Cable Management Box) 415 557 showTitle
(6016478556318) 456 498 showCode
(LOT-000002) 45 447 showTitle
(LOT-000002) 85 388 showCode
(LOT-000003) 230 447 showTitle
(LOT-000003) 271 388 showCode
(Validate) 415 447 showTitle
(OBTVALI) 456 388 showCode
(Internal transfer (activate Storage Locations)) 45 357 showLabel
(WH/Stock) 45 337 showTitle
(WHSTOCK) 85 278 showCode
(Pedal Bin) 230 337 showTitle
(6016478556493) 271 278 showCode
(WH/Stock/Shelf1) 415 337 showTitle
(SHELF1) 456 278 showCode
(Validate) 45 227 showTitle
(OBTVALI) 85 168 showCode


(Put in Pack (activate Packages)) 45 137 showLabel
(YourCompany Receipts) 45 117 showTitle
(WHIN) 85 58 showCode
(Large Cabinet) 230 117 showTitle
(6016478556509) 271 58 showCode
(Put in Pack) 415 117 showTitle
(OBTPACK) 456 58 showCode

(Don't have any barcode scanner? Right click on your screen > Inspect > Console and type the following command:) 45 35 showFooter
(   odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", {barcode:"setyourbarcodehere"})) 45 25 showFooter
(and replace "setyourbarcodehere" by the barcode you would like to scan OR use our mobile app.) 45 15 showFooter
HEADER

# pg 2 of demo barcodes. Some blanks may exist due to flows having a rows with less than 3 barcodes.
barcode -t 3x7+20+35 -m 25x30 -p "210x297mm" -e code128b -n > barcodes_demo_barcode_pg_2.ps  << BARCODES
OBTVALI


BATCH/00002
6016478556370
6016478556516
6016478556356
OBTVALI

BATCH/00001
6016478556523
CLUSTER-PACK-1
6016478556530
CLUSTER-PACK-1
6016478556516
CLUSTER-PACK-2
OBTVALI

BARCODES

cat > barcodes_demo_header_pg_2.ps << HEADER
/showLabel { /Helvetica findfont 14 scalefont setfont moveto show } def
/showTitle { /Helvetica findfont 11 scalefont setfont moveto show } def
/showCode { /Helvetica findfont 8 scalefont setfont moveto show } def
/showFooter { /Helvetica findfont 8 scalefont setfont moveto show } def
(Validate) 45 777 showTitle
(OBTVALI) 85 718 showCode


(Batch picking (activate Batch Pickings)) 45 687 showLabel
(BATCH/00002) 45 667 showTitle
(BATCH/00002) 85 608 showCode
(Large Meeting Table) 230 667 showTitle
(6016478556370) 271 608 showCode
(Four Person Desk) 415 667 showTitle
(6016478556516) 456 608 showCode
(Three-Seat Sofa) 45 557 showTitle
(6016478556356) 85 498 showCode
(Validate) 230 557 showTitle
(OBTVALI) 271 498 showCode

(Batch picking with cluster pickings (activate Batch Pickings and Packages)) 45 467 showLabel
(BATCH/00001) 45 447 showTitle
(BATCH/00001) 85 388 showCode
(Cabinet with Doors) 230 447 showTitle
(6016478556523) 271 388 showCode
(CLUSTER-PACK-1) 415 447 showTitle
(CLUSTER-PACK-1) 456 388 showCode
(Acoustic Bloc Screens) 45 337 showTitle
(6016478556530) 85 278 showCode
(CLUSTER-PACK-1) 230 337 showTitle
(CLUSTER-PACK-1) 271 278 showCode
(Four Person Desk) 415 337 showTitle
(6016478556516) 456 278 showCode
(CLUSTER-PACK-2) 45 227 showTitle
(CLUSTER-PACK-2) 85 168 showCode
(Validate) 230 227 showTitle
(OBTVALI) 271 168 showCode

(Don't have any barcode scanner? Right click on your screen > Inspect > Console and type the following command:) 45 35 showFooter
(   odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", {barcode:"setyourbarcodehere"})) 45 25 showFooter
(and replace "setyourbarcodehere" by the barcode you would like to scan OR use our mobile app.) 45 15 showFooter
HEADER

cat barcodes_demo_header_pg_1.ps barcodes_demo_barcode_pg_1.ps barcodes_demo_header_pg_2.ps barcodes_demo_barcode_pg_2.ps | ps2pdf - - > barcodes_demo.pdf
rm barcodes_demo_header_pg_1.ps barcodes_demo_barcode_pg_1.ps
rm barcodes_demo_header_pg_2.ps barcodes_demo_barcode_pg_2.ps

python3 make_barcodes.py
