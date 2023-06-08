var Tremol = Tremol || { };
Tremol.FP = Tremol.FP || function () { };
Tremol.FP.prototype.timeStamp = 2011061631;
/**
 * Opens the cash drawer.
 */
Tremol.FP.prototype.CashDrawerOpen = function () {
	return this.do('CashDrawerOpen');
};

/**
 * Paying the exact amount in cash and close the fiscal receipt.
 */
Tremol.FP.prototype.CashPayCloseReceipt = function () {
	return this.do('CashPayCloseReceipt');
};

/**
 * Clears the external display.
 */
Tremol.FP.prototype.ClearDisplay = function () {
	return this.do('ClearDisplay');
};

/**
 * Closes the non-fiscal receipt.
 */
Tremol.FP.prototype.CloseNonFiscReceipt = function () {
	return this.do('CloseNonFiscReceipt');
};

/**
 * Close the fiscal receipt (Fiscal receipt, Storno receipt, or Non-fical receipt). When the payment is finished.
 */
Tremol.FP.prototype.CloseReceipt = function () {
	return this.do('CloseReceipt');
};

/**
 * Confirm storing VAT and ID numbers into the operative memory.
 * @param {string} Password 6 symbols string
 */
Tremol.FP.prototype.ConfirmIDNumandVATnum = function (Password) {
	return this.do('ConfirmIDNumandVATnum', 'Password', Password);
};

/**
 * Start paper cutter. The command works only in fiscal printer devices.
 */
Tremol.FP.prototype.CutPaper = function () {
	return this.do('CutPaper');
};

/**
 * Executes the direct command .
 * @param {string} Input Raw request to FP
 * @return {string}
 */
Tremol.FP.prototype.DirectCommand = function (Input) {
	return this.do('DirectCommand', 'Input', Input);
};

/**
 * Shows the current date and time on the external display.
 */
Tremol.FP.prototype.DisplayDateTime = function () {
	return this.do('DisplayDateTime');
};

/**
 * Shows a 20-symbols text in the upper external display line.
 * @param {string} Text 20 symbols text
 */
Tremol.FP.prototype.DisplayTextLine1 = function (Text) {
	return this.do('DisplayTextLine1', 'Text', Text);
};

/**
 * Shows a 20-symbols text in the lower external display line.
 * @param {string} Text 20 symbols text
 */
Tremol.FP.prototype.DisplayTextLine2 = function (Text) {
	return this.do('DisplayTextLine2', 'Text', Text);
};

/**
 * Shows a 20-symbols text in the first line and last 20-symbols text in the second line of the external display lines.
 * @param {string} Text 40 symbols text
 */
Tremol.FP.prototype.DisplayTextLines1and2 = function (Text) {
	return this.do('DisplayTextLines1and2', 'Text', Text);
};

/**
 * Enter Service mode
 * @param {Tremol.Enums.OptionServiceMode} OptionServiceMode 1 symbol:  
-'1' - Service mode 
-'0' - Sales mode
 * @param {string} ServicePassword 8 ASCII symbols
 */
Tremol.FP.prototype.EnterServiceMode = function (OptionServiceMode, ServicePassword) {
	return this.do('EnterServiceMode', 'OptionServiceMode', OptionServiceMode, 'ServicePassword', ServicePassword);
};

/**
 * Temporary enable/disable detailed receipts info sending
 * @param {Tremol.Enums.OptionActivationRS} OptionActivationRS 1 symbol of value 
- '1' - Yes 
- '0' - No
 */
Tremol.FP.prototype.ManageDetailedReceiptInfoSending = function (OptionActivationRS) {
	return this.do('ManageDetailedReceiptInfoSending', 'OptionActivationRS', OptionActivationRS);
};

/**
 * Temporary enable/disable short receipts sending
 * @param {Tremol.Enums.OptionActivationRS} OptionActivationRS 1 symbol with value : 
- '1' - Yes 
- '0' - No
 */
Tremol.FP.prototype.ManageShortReceiptSending = function (OptionActivationRS) {
	return this.do('ManageShortReceiptSending', 'OptionActivationRS', OptionActivationRS);
};

/**
 * Opens a non-fiscal receipt assigned to the specified operator
 * @param {number} OperNum Symbols from '1' to '20' corresponding to operator's number
 * @param {string} OperPass 4 symbols for operator's password
 */
Tremol.FP.prototype.OpenNonFiscalReceipt = function (OperNum, OperPass) {
	return this.do('OpenNonFiscalReceipt', 'OperNum', OperNum, 'OperPass', OperPass);
};

/**
 * Opens a fiscal receipt assigned to the specified operator
 * @param {number} OperNum Symbol from 1 to 20 corresponding to operator's number
 * @param {string} OperPass 4 symbols for operator's password
 * @param {Tremol.Enums.OptionReceiptType} OptionReceiptType 1 symbol with value: 
 - '1' - Sale 
 - '0' - Storno
 * @param {Tremol.Enums.OptionPrintType} OptionPrintType 1 symbol with value 
 - '0' - Step by step printing 
 - '2' - Postponed printing
 */
Tremol.FP.prototype.OpenReceiptOrStorno = function (OperNum, OperPass, OptionReceiptType, OptionPrintType) {
	return this.do('OpenReceiptOrStorno', 'OperNum', OperNum, 'OperPass', OperPass, 'OptionReceiptType', OptionReceiptType, 'OptionPrintType', OptionPrintType);
};

/**
 * Feeds one line of paper.
 */
Tremol.FP.prototype.PaperFeed = function () {
	return this.do('PaperFeed');
};

/**
 * Register the payment in the receipt with specified type of payment and exact amount received.
 * @param {Tremol.Enums.OptionPaymentType} OptionPaymentType 1 symbol with values  
 - '0' - Cash 
 - '1' - Card  
 - '2' - Voucher  
 - '3' - Credit 
 - '4' - Currency
 */
Tremol.FP.prototype.PayExactSum = function (OptionPaymentType) {
	return this.do('PayExactSum', 'OptionPaymentType', OptionPaymentType);
};

/**
 * Registers the payment in the receipt with specified type of payment and amount received.
 * @param {Tremol.Enums.OptionPaymentType} OptionPaymentType 1 symbol with values  
 - '0' - Cash 
 - '1' - Card  
 - '2' - Voucher  
 - '3' - Credit 
 - '4' - Currency
 * @param {Tremol.Enums.OptionChange} OptionChange Default value is 0, 1 symbol with value: 
 - '0 - With Change 
 - '1' - Without Change
 * @param {number} Amount Up to 10 characters for received amount
 * @param {Tremol.Enums.OptionChangeType=} OptionChangeType 1 symbols with value: 
 - '0' - Change In Cash 
 - '1' - Same As The payment 
 - '2' - Change In Currency
 */
Tremol.FP.prototype.Payment = function (OptionPaymentType, OptionChange, Amount, OptionChangeType) {
	return this.do('Payment', 'OptionPaymentType', OptionPaymentType, 'OptionChange', OptionChange, 'Amount', Amount, 'OptionChangeType', OptionChangeType);
};

/**
 * Prints an article report with or without zeroing ('Z' or 'X').
 * @param {Tremol.Enums.OptionZeroing} OptionZeroing with following values: 
 - 'Z' - Zeroing 
 - 'X' - Without zeroing
 */
Tremol.FP.prototype.PrintArticleReport = function (OptionZeroing) {
	return this.do('PrintArticleReport', 'OptionZeroing', OptionZeroing);
};

/**
 * Prints barcode from type stated by CodeType and CodeLen and with data stated in CodeData field.
 * @param {Tremol.Enums.OptionCodeType} OptionCodeType 1 symbol with possible values: 
 - '0' - UPC A 
 - '1' - UPC E 
 - '2' - EAN 13 
 - '3' - EAN 8 
 - '4' - CODE 39 
 - '5' - ITF 
 - '6' - CODABAR 
 - 'H' - CODE 93 
 - 'I' - CODE 128
 * @param {number} CodeLen 1..2 bytes for number of bytes according to the table
 * @param {string} CodeData From 0 to 255 bytes data in range according to the table
 */
Tremol.FP.prototype.PrintBarcode = function (OptionCodeType, CodeLen, CodeData) {
	return this.do('PrintBarcode', 'OptionCodeType', OptionCodeType, 'CodeLen', CodeLen, 'CodeData', CodeData);
};

/**
 * Print a brief FM report by initial and end date.
 * @param {Date} StartDate 6 symbols for initial date in the DDMMYY format
 * @param {Date} EndDate 6 symbols for final date in the DDMMYY format
 */
Tremol.FP.prototype.PrintBriefFMReportByDate = function (StartDate, EndDate) {
	return this.do('PrintBriefFMReportByDate', 'StartDate', StartDate, 'EndDate', EndDate);
};

/**
 * Print a brief FM report by initial and end FM report number.
 * @param {number} StartNum 4 symbols for the initial FM report number included in report, format ####
 * @param {number} EndNum 4 symbols for the final FM report number included in report, format ####
 */
Tremol.FP.prototype.PrintBriefFMReportByNum = function (StartNum, EndNum) {
	return this.do('PrintBriefFMReportByNum', 'StartNum', StartNum, 'EndNum', EndNum);
};

/**
 * Depending on the parameter prints:  − daily fiscal report with zeroing and fiscal memory record, preceded by Electronic Journal report print ('Z'); − daily fiscal report without zeroing ('X');
 * @param {Tremol.Enums.OptionZeroing} OptionZeroing 1 character with following values: 
 - 'Z' - Zeroing 
 - 'X' - Without zeroing
 */
Tremol.FP.prototype.PrintDailyReport = function (OptionZeroing) {
	return this.do('PrintDailyReport', 'OptionZeroing', OptionZeroing);
};

/**
 * Print a department report with or without zeroing ('Z' or 'X').
 * @param {Tremol.Enums.OptionZeroing} OptionZeroing 1 symbol with value: 
 - 'Z' - Zeroing 
 - 'X' - Without zeroing
 */
Tremol.FP.prototype.PrintDepartmentReport = function (OptionZeroing) {
	return this.do('PrintDepartmentReport', 'OptionZeroing', OptionZeroing);
};

/**
 * Prints a detailed FM report by initial and end date.
 * @param {Date} StartDate 6 symbols for initial date in the DDMMYY format
 * @param {Date} EndDate 6 symbols for final date in the DDMMYY format
 */
Tremol.FP.prototype.PrintDetailedFMReportByDate = function (StartDate, EndDate) {
	return this.do('PrintDetailedFMReportByDate', 'StartDate', StartDate, 'EndDate', EndDate);
};

/**
 * Print a detailed FM report by initial and end FM report number.
 * @param {number} StartNum 4 symbols for the initial report number included in report, format ####
 * @param {number} EndNum 4 symbols for the final report number included in report, format ####
 */
Tremol.FP.prototype.PrintDetailedFMReportByNum = function (StartNum, EndNum) {
	return this.do('PrintDetailedFMReportByNum', 'StartNum', StartNum, 'EndNum', EndNum);
};

/**
 * Prints out a diagnostic receipt.
 */
Tremol.FP.prototype.PrintDiagnostics = function () {
	return this.do('PrintDiagnostics');
};

/**
 * Print or store Electronic Journal report with all documents.
 */
Tremol.FP.prototype.PrintEJ = function () {
	return this.do('PrintEJ');
};

/**
 * Printing Electronic Journal Report from Report initial date to report Final date.
 * @param {Date} StartRepFromDate 6 symbols for initial date in the DDMMYY format
 * @param {Date} EndRepFromDate 6 symbols for final date in the DDMMYY format
 */
Tremol.FP.prototype.PrintEJByDate = function (StartRepFromDate, EndRepFromDate) {
	return this.do('PrintEJByDate', 'StartRepFromDate', StartRepFromDate, 'EndRepFromDate', EndRepFromDate);
};

/**
 * Printing Electronic Journal Report from receipt number to receipt number.
 * @param {string} ZrepNum 4 symbols for Z report number
 * @param {number} StartReceiptNum 5 symbols in format ###### for initial receipt number 
included in report.
 * @param {number} EndReceiptNum 5 symbols in format ###### for final receipt number included 
in report.
 */
Tremol.FP.prototype.PrintEJByReceiptNumFromZrep = function (ZrepNum, StartReceiptNum, EndReceiptNum) {
	return this.do('PrintEJByReceiptNumFromZrep', 'ZrepNum', ZrepNum, 'StartReceiptNum', StartReceiptNum, 'EndReceiptNum', EndReceiptNum);
};

/**
 * Printing Electronic Journal Report from receipt number to receipt number.
 * @param {string} ZrepNum 4 symbols for Z report number
 * @param {string} StartReceiptNum 5 symbols for initial daily Storno receipt number
 * @param {string} EndReceiptNum 5 symbols for final daily Storno receipt number
 */
Tremol.FP.prototype.PrintEJByStornoNumFromZrep = function (ZrepNum, StartReceiptNum, EndReceiptNum) {
	return this.do('PrintEJByStornoNumFromZrep', 'ZrepNum', ZrepNum, 'StartReceiptNum', StartReceiptNum, 'EndReceiptNum', EndReceiptNum);
};

/**
 * Print or store Electronic Journal Report from by number of Z report blocks.
 * @param {number} StartZNum 4 symbols for initial number report in format ####
 * @param {number} EndZNum 4 symbols for final number report in format ####
 */
Tremol.FP.prototype.PrintEJByZBlocks = function (StartZNum, EndZNum) {
	return this.do('PrintEJByZBlocks', 'StartZNum', StartZNum, 'EndZNum', EndZNum);
};

/**
 * Prints the programmed graphical logo with the stated number.
 * @param {number} Number Number of logo to be printed. If missing prints logo with number 0
 */
Tremol.FP.prototype.PrintLogo = function (Number) {
	return this.do('PrintLogo', 'Number', Number);
};

/**
 * Prints an operator's report for a specified operator (0 = all operators) with or without zeroing ('Z' or 'X'). When a 'Z' value is specified the report should include all operators.
 * @param {Tremol.Enums.OptionZeroing} OptionZeroing with following values: 
 - 'Z' - Zeroing 
 - 'X' - Without zeroing
 * @param {number} Number Symbols from 0 to 20corresponding to operator's number 
,0 for all operators
 */
Tremol.FP.prototype.PrintOperatorReport = function (OptionZeroing, Number) {
	return this.do('PrintOperatorReport', 'OptionZeroing', OptionZeroing, 'Number', Number);
};

/**
 * Print whole special FM events report.
 */
Tremol.FP.prototype.PrintSpecialEventsFMreport = function () {
	return this.do('PrintSpecialEventsFMreport');
};

/**
 * Print a free text. The command can be executed only if receipt is opened (Fiscal receipt, Storno receipt or Non-fical receipt). In the beginning and in the end of line symbol '#' is printed.
 * @param {string} Text TextLength-2 symbols
 */
Tremol.FP.prototype.PrintText = function (Text) {
	return this.do('PrintText', 'Text', Text);
};

/**
 * Stores a block containing the number format into the fiscal memory. Print the current status on the printer.
 * @param {string} Password 6-symbols string
 * @param {Tremol.Enums.OptionDecimalPointPosition} OptionDecimalPointPosition 1 symbol with values: 
 - '0'- Whole numbers 
 - '2' - Fractions
 */
Tremol.FP.prototype.ProgDecimalPointPosition = function (Password, OptionDecimalPointPosition) {
	return this.do('ProgDecimalPointPosition', 'Password', Password, 'OptionDecimalPointPosition', OptionDecimalPointPosition);
};

/**
 * Set data for the state department number from the internal FD database.
 * @param {number} Number 2 symbols department number in format ##
 * @param {string} Name 23 characters department name
 * @param {Tremol.Enums.OptionVATClass} OptionVATClass 1 character for VAT class: 
 - 'А' - VAT Class 0 
 - 'Б' - VAT Class 1 
 - 'В' - VAT Class 2 
 - 'Г' - VAT Class 3
 * @param {number} Price Up to 10 symbols for department price
 * @param {string} FlagsPrice 1 symbol with value: 
Flags.7=1 
Flags.6=0 
Flags.5=0 
Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) 
Flags.3=0 
Flags.2=1 Yes, Flags.2=0 No (Single Transaction) 
Flags.1=1 Yes, Flags.1=0 No (Free price limited) 
Flags.0=1 Yes, Flags.0=0 No (Free price enabled)
 */
Tremol.FP.prototype.ProgDepartment = function (Number, Name, OptionVATClass, Price, FlagsPrice) {
	return this.do('ProgDepartment', 'Number', Number, 'Name', Name, 'OptionVATClass', OptionVATClass, 'Price', Price, 'FlagsPrice', FlagsPrice);
};

/**
 * Program the contents of a Display Greeting message.
 * @param {string} DisplayGreetingText 20 symbols for Display greeting message
 */
Tremol.FP.prototype.ProgDisplayGreetingMessage = function (DisplayGreetingText) {
	return this.do('ProgDisplayGreetingMessage', 'DisplayGreetingText', DisplayGreetingText);
};

/**
 * Programs the external display.
 * @param {string} Password A 6-symbol string
 */
Tremol.FP.prototype.ProgExtDisplay = function (Password) {
	return this.do('ProgExtDisplay', 'Password', Password);
};

/**
 * Program the contents of a footer lines.
 * @param {Tremol.Enums.OptionFooterLine} OptionFooterLine 2 symbol with value: 
-'F1' - Footer 1 
-'F2' - Footer 2 
-'F3' - Footer 3
 * @param {string} FooterText TextLength symbols for footer line
 */
Tremol.FP.prototype.ProgFooter = function (OptionFooterLine, FooterText) {
	return this.do('ProgFooter', 'OptionFooterLine', OptionFooterLine, 'FooterText', FooterText);
};

/**
 * Program the contents of a header lines.
 * @param {Tremol.Enums.OptionHeaderLine} OptionHeaderLine 1 symbol with value: 
 - '1' - Header 1 
 - '2' - Header 2 
 - '3' - Header 3 
 - '4' - Header 4 
 - '5' - Header 5 
 - '6' - Header 6 
 - '7' - ID number 
 - '8' - VAT number
 * @param {string} HeaderText TextLength symbols for header lines
 */
Tremol.FP.prototype.ProgHeader = function (OptionHeaderLine, HeaderText) {
	return this.do('ProgHeader', 'OptionHeaderLine', OptionHeaderLine, 'HeaderText', HeaderText);
};

/**
 * Programs the operator's name and password.
 * @param {number} Number Symbols from '1' to '20' corresponding to operator's number
 * @param {string} Name 20 symbols for operator's name
 * @param {string} Password 6 symbols for operator's password
 */
Tremol.FP.prototype.ProgOperator = function (Number, Name, Password) {
	return this.do('ProgOperator', 'Number', Number, 'Name', Name, 'Password', Password);
};

/**
 * Programs the number of POS, printing of logo, cash drawer opening, cutting permission, external display management mode, article report type, enable or disable currency in receipt and working operators counter.
 * @param {number} POSNum 4 symbols for number of POS in format ####
 * @param {Tremol.Enums.OptionPrintLogo} OptionPrintLogo 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @param {Tremol.Enums.OptionAutoOpenDrawer} OptionAutoOpenDrawer 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @param {Tremol.Enums.OptionAutoCut} OptionAutoCut 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @param {Tremol.Enums.OptionExternalDispManagement} OptionExternalDispManagement 1 symbol of value: 
 - '1' - Manual 
 - '0' - Auto
 * @param {Tremol.Enums.OptionArticleReportType} OptionArticleReportType 1 symbol of value: 
 - '1' - Detailed 
 - '0' - Brief
 * @param {Tremol.Enums.OptionEnableCurrency} OptionEnableCurrency 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @param {Tremol.Enums.OptionWorkOperatorCount} OptionWorkOperatorCount 1 symbol of value: 
 - '1' - One 
 - '0' - More
 */
Tremol.FP.prototype.ProgParameters = function (POSNum, OptionPrintLogo, OptionAutoOpenDrawer, OptionAutoCut, OptionExternalDispManagement, OptionArticleReportType, OptionEnableCurrency, OptionWorkOperatorCount) {
	return this.do('ProgParameters', 'POSNum', POSNum, 'OptionPrintLogo', OptionPrintLogo, 'OptionAutoOpenDrawer', OptionAutoOpenDrawer, 'OptionAutoCut', OptionAutoCut, 'OptionExternalDispManagement', OptionExternalDispManagement, 'OptionArticleReportType', OptionArticleReportType, 'OptionEnableCurrency', OptionEnableCurrency, 'OptionWorkOperatorCount', OptionWorkOperatorCount);
};

/**
 * Program the name of the payment types.
 * @param {Tremol.Enums.OptionPaymentNum} OptionPaymentNum 1 symbol for payment type: 
 - '1' - Payment 1 
 - '2' - Payment 2 
 - '3' - Payment 3 
 - '4' - Payment 4
 * @param {string} Name 10 symbols for payment type name
 * @param {number=} Rate 10 symbols for exchange rate in format: ####.#####  
of the 4
th
 payment type.
 */
Tremol.FP.prototype.ProgPayment = function (OptionPaymentNum, Name, Rate) {
	return this.do('ProgPayment', 'OptionPaymentNum', OptionPaymentNum, 'Name', Name, 'Rate', Rate);
};

/**
 * Program the Barcode number for a certain article (item) from the internal database.
 * @param {number} PLUNum 5 symbols for article number in format: #####
 * @param {string} Barcode 13 symbols for barcode
 */
Tremol.FP.prototype.ProgPLUbarcode = function (PLUNum, Barcode) {
	return this.do('ProgPLUbarcode', 'PLUNum', PLUNum, 'Barcode', Barcode);
};

/**
 * Programs the general data for a certain article in the internal FD database. The price may have variable length, while the name field is fixed.
 * @param {string} PLUNum 5 symbols for article number
 * @param {string} PLUName 32 symbols for article name
 * @param {number} Price 1 to 10 symbols for article price
 * @param {string} FlagsPriceQty 1 symbols with value: 
Flags.7=1 
Flags.6=0 
Flags.5=0 
Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) 
Flags.3=1 Yes, Flags.3=0 No (Allow negative quantity) 
Flags.2=1 Yes, Flags.2=0 No (Monitoring quantity in stock) 
Flags.1=1 Yes, Flags.1=0 No (Free price limited) 
Flags.0=1 Yes, Flags.0=0 No (Free price enabled)
 * @param {number} BelongToDepNum BelongToDepNum + 80h, 1 symbol for article 
department attachment, formed in the following manner: 
BelongToDepNum[HEX] + 80h example: Dep01 = 81h, Dep02 = 82h … 
Dep19 = 93h
 * @param {number} AvailableQuantity Up to 11 symbols for quantity in stock
 * @param {string} Barcode 13 symbols for barcode
 */
Tremol.FP.prototype.ProgPLUgeneral = function (PLUNum, PLUName, Price, FlagsPriceQty, BelongToDepNum, AvailableQuantity, Barcode) {
	return this.do('ProgPLUgeneral', 'PLUNum', PLUNum, 'PLUName', PLUName, 'Price', Price, 'FlagsPriceQty', FlagsPriceQty, 'BelongToDepNum', BelongToDepNum, 'AvailableQuantity', AvailableQuantity, 'Barcode', Barcode);
};

/**
 * Program the price for a certain article from the internal database.
 * @param {number} PLUNum 5 symbols for article number in format: #####
 * @param {number} Price Up to 10 symbols for article price
 * @param {Tremol.Enums.OptionPrice} OptionPrice 1 byte for Price flag with next value: 
 - '0'- Free price is disable valid only programmed price 
 - '1'- Free price is enable 
 - '2'- Limited price
 */
Tremol.FP.prototype.ProgPLUprice = function (PLUNum, Price, OptionPrice) {
	return this.do('ProgPLUprice', 'PLUNum', PLUNum, 'Price', Price, 'OptionPrice', OptionPrice);
};

/**
 * Programs available quantity and quantiy type for a certain article in the internal database.
 * @param {number} PLUNum 5 symbols for article number in format: #####
 * @param {number} AvailableQuantity Up to 11 symbols for quantity in stock
 * @param {Tremol.Enums.OptionQuantityType} OptionQuantityType 1 symbol for Quantity flag with next value:  
 - '0'- Availability of PLU stock is not monitored  
 - '1'- Disable negative quantity  
 - '2'- Enable negative quantity
 */
Tremol.FP.prototype.ProgPLUqty = function (PLUNum, AvailableQuantity, OptionQuantityType) {
	return this.do('ProgPLUqty', 'PLUNum', PLUNum, 'AvailableQuantity', AvailableQuantity, 'OptionQuantityType', OptionQuantityType);
};

/**
 * Stores a block containing the values of the VAT rates into the fiscal memory. Print the values on the printer.
 * @param {string} Password 6 symbols string
 * @param {number} VATrate1 Value of VAT rate А from 6 symbols in format ##.##
 * @param {number} VATrate2 Value of VAT rate Б from 6 symbols in format ##.##
 * @param {number} VATrate3 Value of VAT rate В from 6 symbols in format ##.##
 * @param {number} VATrate4 Value of VAT rate Г from 6 symbols in format ##.##
 */
Tremol.FP.prototype.ProgVATrates = function (Password, VATrate1, VATrate2, VATrate3, VATrate4) {
	return this.do('ProgVATrates', 'Password', Password, 'VATrate1', VATrate1, 'VATrate2', VATrate2, 'VATrate3', VATrate3, 'VATrate4', VATrate4);
};

/**
 *  Reads raw bytes from FP.
 * @param {number} Count How many bytes to read if EndChar is not specified
 * @param {string} EndChar The character marking the end of the data. If present Count parameter is ignored.
 * @return {Uint8Array}
 */
Tremol.FP.prototype.RawRead = function (Count, EndChar) {
	return this.do('RawRead', 'Count', Count, 'EndChar', EndChar);
};

/**
 *  Writes raw bytes to FP 
 * @param {Uint8Array} Bytes The bytes in BASE64 ecoded string to be written to FP
 */
Tremol.FP.prototype.RawWrite = function (Bytes) {
	return this.do('RawWrite', 'Bytes', Bytes);
};

/**
 * @typedef {Object} CurrentRecInfoRes
 * @property {Tremol.Enums.OptionIsReceiptOpened} OptionIsReceiptOpened 1 symbol with value: 
 - '0' - No 
 - '1' - Yes
 * @property {Tremol.Enums.OptionReceiptType} OptionReceiptType 1 symbol with value: 
 - '1' - Sale  
 - '0' - Storno
 * @property {string} SalesNumber 3 symbols for number of sales
 * @property {string} MacSubtotalVATG0 11 symbols for subtotal from Macedonian goods by VAT groups
 * @property {string} MacSubtotalVATG1 11 symbols for subtotal from Macedonian goods by VAT groups
 * @property {string} MacSubtotalVATG2 11 symbols for subtotal from Macedonian goods by VAT groups
 * @property {string} MacSubtotalVATG3 11 symbols for subtotal from Macedonian goods by VAT groups
 * @property {string} ImpSubtotalVATG0 11 symbols for subtotal from imported goods by VAT groups
 * @property {string} ImpSubtotalVATG1 11 symbols for subtotal from imported goods by VAT groups
 * @property {string} ImpSubtotalVATG2 11 symbols for subtotal from imported goods by VAT groups
 * @property {string} ImpSubtotalVATG3 11 symbols for subtotal from imported goods by VAT groups
 * @property {Tremol.Enums.OptionInitiatedPayment} OptionInitiatedPayment 1 symbol with value: 
 - '1' - initiated payment 
 - '0' - not initiated payment
 * @property {Tremol.Enums.OptionFinalizedPayment} OptionFinalizedPayment 1 symbol with value: 
 - '1' - finalized payment 
 - '0' - not finalized payment
 * @property {Tremol.Enums.OptionPowerDownInReceipt} OptionPowerDownInReceipt 1 symbol with value: 
- '0' - No 
- '1' - Yes
 * @property {number} ChangeAmount Up to 11 symbols the amount of the due change in the stated payment 
type
 * @property {Tremol.Enums.OptionChangeType} OptionChangeType 1 symbols with value: 
 - '0' - Change In Cash 
 - '1' - Same As The payment 
 - '2' - Change In Currency
 */

/**
 * Read the current status of the receipt.
 * @return {CurrentRecInfoRes}
 */
Tremol.FP.prototype.ReadCurrentRecInfo = function () {
	return this.do('ReadCurrentRecInfo');
};

/**
 * @typedef {Object} DailyCountersRes
 * @property {number} TotalReciepts 5 symbols for total number of fiscal receipts
 * @property {number} TotalStorno 5 symbols for total number of Storno receipts
 * @property {number} NumLastFMBlock Up to 5 symbols for number of the last FM report
 * @property {number} NumEJ Up to 5 symbols for number of EJ
 * @property {Date} DateTime 16 symbols for date and time of the last block storage in FM in format 
"DD-MM-YYYY HH:MM"
 */

/**
 * Provides information about the total fiscal counters and last Z- report date and time.
 * @return {DailyCountersRes}
 */
Tremol.FP.prototype.ReadDailyCounters = function () {
	return this.do('ReadDailyCounters');
};

/**
 * @typedef {Object} DailyCountersByOperatorRes
 * @property {number} OperNum Symbols from 1 to 20 corresponding to operator's number
 * @property {number} WorkOperatorsCounter Up to 5 symbols for number of the work operators
 * @property {Date} LastOperatorReportDateTime 16 symbols for date and time of the last operator's report in 
format DD-MM-YYYY HH:MM
 */

/**
 * Read the last operator's report number and date and time.
 * @param {number} OperNum Symbols from 1 to 20 corresponding to 
operator's number
 * @return {DailyCountersByOperatorRes}
 */
Tremol.FP.prototype.ReadDailyCountersByOperator = function (OperNum) {
	return this.do('ReadDailyCountersByOperator', 'OperNum', OperNum);
};

/**
 * @typedef {Object} DailyGeneralRegistersByOperatorRes
 * @property {number} OperNum Symbols from 1 to 20 corresponding to operator's number
 * @property {number} FiscalReciept Up to 5 symbols for daily number of fiscal receipts
 * @property {number} StornoReciept Up to 5 symbols for daily number of Storno receipts
 * @property {number} DiscountsNum Up to 5 symbols for number of discounts
 * @property {number} DiscountsAmount Up to 11 symbols for accumulated amount of discounts
 * @property {number} AdditionsNum Up to 5 symbols for number of additions
 * @property {number} AdditionsAmount Up to 11 symbols for accumulated amount of additions
 */

/**
 * Read the total number of customers, discounts, additions, corrections and accumulated amounts by specified operator.
 * @param {number} OperNum Symbols from 1 to 20 corresponding to operator's number
 * @return {DailyGeneralRegistersByOperatorRes}
 */
Tremol.FP.prototype.ReadDailyGeneralRegistersByOperator = function (OperNum) {
	return this.do('ReadDailyGeneralRegistersByOperator', 'OperNum', OperNum);
};

/**
 * @typedef {Object} DailyPORes
 * @property {number} AmountPayment Up to 11 symbols for PO amount by type of payment
 * @property {number} NumPO Up to 5 symbols for the total number of operations
 */

/**
 * Provides information about the PO amounts by type of payment and the total number of operations.
 * @return {DailyPORes}
 */
Tremol.FP.prototype.ReadDailyPO = function () {
	return this.do('ReadDailyPO');
};

/**
 * @typedef {Object} DailyPObyOperatorRes
 * @property {number} OperNum Symbols from 1 to 20 corresponding to operator's number
 * @property {number} AmountPO_Payments Up to 11 symbols for the PO by type of payment
 * @property {number} NumPO Up to 5 symbols for the total number of operations
 */

/**
 * Provides information about the PO and the total number of operations by specified operator.
 * @param {number} OperNum Symbols from 1 to 20 corresponding to operator's 
number
 * @return {DailyPObyOperatorRes}
 */
Tremol.FP.prototype.ReadDailyPObyOperator = function (OperNum) {
	return this.do('ReadDailyPObyOperator', 'OperNum', OperNum);
};

/**
 * @typedef {Object} DailyRARes
 * @property {number} AmountPayment Up to 11 symbols for RA amounts
 * @property {number} NumRA Up to 5 symbols for the total number of operations
 */

/**
 * Provides information about the RA amounts by type of payment and the total number of operations.
 * @return {DailyRARes}
 */
Tremol.FP.prototype.ReadDailyRA = function () {
	return this.do('ReadDailyRA');
};

/**
 * @typedef {Object} DailyRAbyOperatorRes
 * @property {number} OperNum Symbols from 1 to 20 corresponding to operator's number
 * @property {number} AmountRA_Payments Up to 11 symbols for the RA by type of payment
 * @property {number} NumRA Up to 5 symbols for the total number of operations
 */

/**
 * Provides information about the RA and the total number of operations by specified operator.
 * @param {number} OperNum Symbols from 1 to 20 corresponding to operator's 
number
 * @return {DailyRAbyOperatorRes}
 */
Tremol.FP.prototype.ReadDailyRAbyOperator = function (OperNum) {
	return this.do('ReadDailyRAbyOperator', 'OperNum', OperNum);
};

/**
 * @typedef {Object} DailyReceivedSalesAmountsRes
 * @property {number} AmountPayment Up to 11 symbols for amount received from sales or Storno change by 
cash
 * @property {number} AmountPaymentOthers Up to 11 symbols for amount received from sales or Storno change by 
others payment
 */

/**
 * Provides information about the amounts received from sales and Storno change.
 * @return {DailyReceivedSalesAmountsRes}
 */
Tremol.FP.prototype.ReadDailyReceivedSalesAmounts = function () {
	return this.do('ReadDailyReceivedSalesAmounts');
};

/**
 * @typedef {Object} DailyReceivedSalesAmountsByOperatorRes
 * @property {number} OperNum Symbols from 1 to 20 corresponding to operator's number
 * @property {number} AmountPayment Up to 11 symbols for amount received from sales or Storno change by 
cash
 * @property {number} AmountPaymentOthers Up to 11 symbols for amount received from sales or Storno change by 
others payment
 */

/**
 * Read the amounts received from sales by type of payment and specified operator.
 * @param {number} OperNum Symbols from 1 to 20 corresponding to operator's 
number
 * @return {DailyReceivedSalesAmountsByOperatorRes}
 */
Tremol.FP.prototype.ReadDailyReceivedSalesAmountsByOperator = function (OperNum) {
	return this.do('ReadDailyReceivedSalesAmountsByOperator', 'OperNum', OperNum);
};

/**
 * @typedef {Object} DailyReturnedRes
 * @property {number} AmountPayment Up to 11 symbols for amount received from sales or Storno 
change by cash
 * @property {number} AmountPaymentOthers Up to 11 symbols for amount received from sales or Storno 
change by others payment
 */

/**
 * Provides information about the amounts returned as Storno or sales change.
 * @return {DailyReturnedRes}
 */
Tremol.FP.prototype.ReadDailyReturned = function () {
	return this.do('ReadDailyReturned');
};

/**
 * @typedef {Object} DailyReturnedAmountsRes
 * @property {number} OperNum Symbols from 1 to 20 corresponding to operator's number
 * @property {number} AmountPayment Up to 11 symbols for amount received from sales or Storno change by 
cash
 * @property {number} AmountPaymentOthers Up to 11 symbols for amount received from sales or Storno change by 
others payment
 */

/**
 * Read information about the amounts returned
 * @param {number} OperNum Symbols from 1 to 20 corresponding to operator's 
number
 * @return {DailyReturnedAmountsRes}
 */
Tremol.FP.prototype.ReadDailyReturnedAmounts = function (OperNum) {
	return this.do('ReadDailyReturnedAmounts', 'OperNum', OperNum);
};

/**
 * @typedef {Object} DailySaleAndStornoAmountsByVATRes
 * @property {string} SalesAmountVATGr0 Up to 11 symbols for the amount accumulated from sales by VAT 
group А
 * @property {string} SalesAmountVATGr1 Up to 11 symbols for the amount accumulated from sales by VAT 
group Б
 * @property {string} SalesAmountVATGr2 Up to 11 symbols for the amount accumulated from sales by VAT 
group В
 * @property {string} SalesAmountVATGr3 Up to 11 symbols for the amount accumulated from sales by VAT 
group Г
 * @property {string} SalesMacAmountVATGr0 Up to 11 symbols for the mac amount accumulated from sales by
 * @property {string} SalesMacAmountVATGr1 Up to 11 symbols for the mac amount accumulated from sales by
 * @property {string} SalesMacAmountVATGr2 Up to 11 symbols for the mac amount accumulated from sales by
 * @property {string} SalesMacAmountVATGr3 Up to 11 symbols for the mac amount accumulated from sales by
 * @property {string} StornoAmountVATGr0 Up to 11 symbols for the amount accumulated from Storno by VAT 
group А
 * @property {string} StornoAmountVATGr1 Up to 11 symbols for the amount accumulated from Storno by VAT 
group Б
 * @property {string} StornoAmountVATGr2 Up to 11 symbols for the amount accumulated from Storno by VAT 
group В
 * @property {string} StornoAmountVATGr3 Up to 11 symbols for the amount accumulated from Storno by VAT 
group Г
 * @property {string} StornoMacAmountVATGr0 Up to 11 symbols for the amount accumulated from Mac Storno by
 * @property {string} StornoMacAmountVATGr1 Up to 11 symbols for the amount accumulated from Mac Storno by
 * @property {string} StornoMacAmountVATGr2 Up to 11 symbols for the amount accumulated from Mac Storno by
 * @property {string} StornoMacAmountVATGr3 Up to 11 symbols for the amount accumulated from Mac Storno by
 */

/**
 * Provides information about the accumulated amount by VAT group.
 * @return {DailySaleAndStornoAmountsByVATRes}
 */
Tremol.FP.prototype.ReadDailySaleAndStornoAmountsByVAT = function () {
	return this.do('ReadDailySaleAndStornoAmountsByVAT');
};

/**
 * Provides information about the current date and time.
 * @return {Date}
 */
Tremol.FP.prototype.ReadDateTime = function () {
	return this.do('ReadDateTime');
};

/**
 * Provides information about the current (the last value stored into the FM) decimal point format.
 * @return {Tremol.Enums.OptionDecimalPointPosition}
 */
Tremol.FP.prototype.ReadDecimalPoint = function () {
	return this.do('ReadDecimalPoint');
};

/**
 * @typedef {Object} DepartmentRes
 * @property {number} DepNum 2 symbols for department number in format ##
 * @property {string} DepName 34 symbols for department name
 * @property {Tremol.Enums.OptionVATClass} OptionVATClass 1 character for VAT class attachment of the department: 
 - 'А' - VAT Class 0 
 - 'Б' - VAT Class 1 
 - 'В' - VAT Class 2 
 - 'Г' - VAT Class 3
 * @property {number} Price 1..11 symbols for Department price
 * @property {string} FlagsPrice (Setting price, signle transaction, type of goods) 1 symbol with value: 
Flags.7=1 
Flags.6=0 
Flags.5=0 
Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) 
Flags.3=0 
Flags.2=1 Yes, Flags.2=0 No (Single Transaction) 
Flags.1=1 Yes, Flags.1=0 No (Free price limited) 
Flags.0=1 Yes, Flags.0=0 No (Free price enabled)
 * @property {number} Turnover Up to 11 symbols for accumulated turnover of the department
 * @property {number} SoldQuantity Up to 11 symbols for sold quantity of the department
 * @property {number} TurnoverMac Up to 11 symbols for maced. turnover of the department
 * @property {number} SoldQuantityMac Up to 11 symbols for maced. sold quantity of the department
 * @property {number} TurnoverSt Up to 11 symbols for Storno turnover of the department
 * @property {number} SoldQuantitySt Up to 11 symbols for Storno
 * @property {number} TurnoverStMac Up to 11 symbols for Storno maced.turnover by this department
 * @property {number} SoldQuantityStMac Up to 11 symbols for Storno maced quantity
 * @property {number} LastZReportNumber Up to 5 symbols for the number of last Z report in format #####
 * @property {Date} LastZReportDate 16 symbols for the date and hour in last Z report
 */

/**
 * Provides information for the programmed data, the turnover from the stated department number
 * @param {number} DepNum 2 symbols for deparment number in format: ##
 * @return {DepartmentRes}
 */
Tremol.FP.prototype.ReadDepartment = function (DepNum) {
	return this.do('ReadDepartment', 'DepNum', DepNum);
};

/**
 * Read info for enable/disable detailed receipts
 * @return {Tremol.Enums.OptionActivationRS}
 */
Tremol.FP.prototype.ReadDetailedReceiptInfoSending = function () {
	return this.do('ReadDetailedReceiptInfoSending');
};

/**
 * Provide information about the display greeting message.
 * @return {string}
 */
Tremol.FP.prototype.ReadDisplayGreetingMessage = function () {
	return this.do('ReadDisplayGreetingMessage');
};

/**
 * Read Electronic Journal report with all documents.
 */
Tremol.FP.prototype.ReadEJ = function () {
	return this.do('ReadEJ');
};

/**
 * Read Electronic Journal Report from Report initial date to report Final date.
 * @param {Date} StartRepFromDate 6 symbols for initial date in the DDMMYY format
 * @param {Date} EndRepFromDate 6 symbols for final date in the DDMMYY format
 */
Tremol.FP.prototype.ReadEJByDate = function (StartRepFromDate, EndRepFromDate) {
	return this.do('ReadEJByDate', 'StartRepFromDate', StartRepFromDate, 'EndRepFromDate', EndRepFromDate);
};

/**
 * Read Electronic Journal Report from receipt number to receipt number.
 * @param {string} ZrepNum 4 symbols for Z report number
 * @param {number} StartReceiptNum 5 symbols in format ###### for initial receipt number 
included in report.
 * @param {number} EndReceiptNum 5 symbols in format ###### for final receipt number 
included in report.
 */
Tremol.FP.prototype.ReadEJByReceiptNumFromZrep = function (ZrepNum, StartReceiptNum, EndReceiptNum) {
	return this.do('ReadEJByReceiptNumFromZrep', 'ZrepNum', ZrepNum, 'StartReceiptNum', StartReceiptNum, 'EndReceiptNum', EndReceiptNum);
};

/**
 * Read Electronic Journal Report from receipt number to receipt number.
 * @param {string} ZrepNum 4 symbols for Z report number
 * @param {string} StartReceiptNum 5 symbols for initial daily Storno receipt number
 * @param {string} EndReceiptNum 5 symbols for final daily Storno receipt number
 */
Tremol.FP.prototype.ReadEJByStornoNumFromZrep = function (ZrepNum, StartReceiptNum, EndReceiptNum) {
	return this.do('ReadEJByStornoNumFromZrep', 'ZrepNum', ZrepNum, 'StartReceiptNum', StartReceiptNum, 'EndReceiptNum', EndReceiptNum);
};

/**
 * Read Electronic Journal Report from by number of Z report blocks.
 * @param {number} StartZNum 4 symbols for initial number report in format ####
 * @param {number} EndZNum 4 symbols for final number report in format ####
 */
Tremol.FP.prototype.ReadEJByZBlocks = function (StartZNum, EndZNum) {
	return this.do('ReadEJByZBlocks', 'StartZNum', StartZNum, 'EndZNum', EndZNum);
};

/**
 * Select type of display
 * @return {Tremol.Enums.OptionExternalType}
 */
Tremol.FP.prototype.ReadExternalDisplay = function () {
	return this.do('ReadExternalDisplay');
};

/**
 * Provides consequently information about every single block stored in the FM starting with Acknowledgements and ending with end message.
 */
Tremol.FP.prototype.ReadFMcontent = function () {
	return this.do('ReadFMcontent');
};

/**
 * Read the number of the remaining free records for Z-report in the Fiscal Memory.
 * @return {string}
 */
Tremol.FP.prototype.ReadFMfreeRecords = function () {
	return this.do('ReadFMfreeRecords');
};

/**
 * @typedef {Object} FooterRes
 * @property {Tremol.Enums.OptionFooterLine} OptionFooterLine (Line Number)1 symbol with value: 
 - 'F1' - Footer 1 
 - 'F2' - Footer 2 
 - 'F3' - Footer 3
 * @property {string} FooterText TextLength symbols for footer line
 */

/**
 * Provides the content of the footer lines.
 * @param {Tremol.Enums.OptionFooterLine} OptionFooterLine 1 symbol with value: 
 - 'F1' - Footer 1 
 - 'F2' - Footer 2 
 - 'F3' - Footer 3
 * @return {FooterRes}
 */
Tremol.FP.prototype.ReadFooter = function (OptionFooterLine) {
	return this.do('ReadFooter', 'OptionFooterLine', OptionFooterLine);
};

/**
 * @typedef {Object} GeneralDailyRegistersRes
 * @property {number} FiscalReciept 1..5 symbols for daily number of fiscal receipts
 * @property {number} StornoReciept 1..5 symbols for daily number of Storno receipts
 * @property {number} DiscountsNum Up to 5 symbols for number of discounts
 * @property {number} DiscountsAmount Up to 11 symbols for accumulated amount of discounts
 * @property {number} AdditionsNum Up to 5 symbols for number of additions
 * @property {number} AdditionsAmount Up to 11 symbols for accumulated amount of additions
 */

/**
 * Provides information about the number of customers (number of fiscal receipt issued), number of discounts, additions and corrections made and the accumulated amounts.
 * @return {GeneralDailyRegistersRes}
 */
Tremol.FP.prototype.ReadGeneralDailyRegisters = function () {
	return this.do('ReadGeneralDailyRegisters');
};

/**
 * @typedef {Object} HeaderRes
 * @property {Tremol.Enums.OptionHeaderLine} OptionHeaderLine (Line Number)1 byte with value: 
 - '1' - Header 1 
 - '2' - Header 2 
 - '3' - Header 3 
 - '4' - Header 4 
 - '5' - Header 5 
 - '6' - Header 6 
 - '7' - ID number 
 - '8' - VAT number
 * @property {string} HeaderText TextLength symbols
 */

/**
 * Provides the content of the header lines.
 * @param {Tremol.Enums.OptionHeaderLine} OptionHeaderLine 1 byte with value: 
 - '1' - Header 1 
 - '2' - Header 2 
 - '3' - Header 3 
 - '4' - Header 4 
 - '5' - Header 5 
 - '6' - Header 6 
 - '7' - ID number 
 - '8' - VAT number
 * @return {HeaderRes}
 */
Tremol.FP.prototype.ReadHeader = function (OptionHeaderLine) {
	return this.do('ReadHeader', 'OptionHeaderLine', OptionHeaderLine);
};

/**
 * @typedef {Object} LastDailyReportInfoRes
 * @property {Date} LastZDailyReportDate 10 symbols for last Z-report date in DD-MM-YYYY format
 * @property {number} LastZDailyReportNum Up to 4 symbols for the number of the last daily report
 * @property {number} LastRAMResetNum Up to 4 symbols for the number of the last RAM reset
 */

/**
 * Read date and number of last Z-report and last RAM reset event.
 * @return {LastDailyReportInfoRes}
 */
Tremol.FP.prototype.ReadLastDailyReportInfo = function () {
	return this.do('ReadLastDailyReportInfo');
};

/**
 * @typedef {Object} LastReceiptNumRes
 * @property {number} LastReceiptNum Up to 4 symbols in format #### for the number of last issued fiscal receipt
 * @property {number} LastStornoNum Up to 4 symbols in format #### for the number of last issued Storno receipt
 */

/**
 * Provides information about the number of the last issued receipt.
 * @return {LastReceiptNumRes}
 */
Tremol.FP.prototype.ReadLastReceiptNum = function () {
	return this.do('ReadLastReceiptNum');
};

/**
 * @typedef {Object} OperatorNamePasswordRes
 * @property {number} Number Symbol from 1 to 20 corresponding to the number of operator
 * @property {string} Name 20 symbols for operator's name
 * @property {string} Password 4 symbols for operator's password
 */

/**
 * Provides information about an operator's name and password.
 * @param {number} Number Symbol from 1 to 20 corresponding to the number of operator
 * @return {OperatorNamePasswordRes}
 */
Tremol.FP.prototype.ReadOperatorNamePassword = function (Number) {
	return this.do('ReadOperatorNamePassword', 'Number', Number);
};

/**
 * @typedef {Object} ParametersRes
 * @property {number} POSNum (POS Number) 4 symbols for number of POS in format ####
 * @property {Tremol.Enums.OptionPrintLogo} OptionPrintLogo (Print Logo) 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @property {Tremol.Enums.OptionAutoOpenDrawer} OptionAutoOpenDrawer (Auto Open Drawer) 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @property {Tremol.Enums.OptionAutoCut} OptionAutoCut (Auto Cut) 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @property {Tremol.Enums.OptionExternalDispManagement} OptionExternalDispManagement (External Display Management) 1 symbol of value: 
 - '1' - Manual 
 - '0' - Auto
 * @property {Tremol.Enums.OptionRecieptSend} OptionRecieptSend 1 symbol of value: 
- '1' - automatic sending 
- '0' - without sending
 * @property {Tremol.Enums.OptionEnableCurrency} OptionEnableCurrency (Enable Currency) 1 symbol of value: 
 - '1' - Yes 
 - '0' - No
 * @property {Tremol.Enums.OptionWorkOperatorCount} OptionWorkOperatorCount (Work Operator Count) 1 symbol of value: 
 - '1' - One 
 - '0' - More
 */

/**
 * Provides information about the programmed number of POS and the current values of the logo, cutting permission, display mode, enable/disable currency in receipt.
 * @return {ParametersRes}
 */
Tremol.FP.prototype.ReadParameters = function () {
	return this.do('ReadParameters');
};

/**
 * @typedef {Object} PaymentsRes
 * @property {string} NamePaym0 10 symbols for type 0 of payment name
 * @property {string} NamePaym1 10 symbols for type 1 of payment name
 * @property {string} NamePaym2 10 symbols for type 2 of payment name
 * @property {string} NamePaym3 10 symbols for type 3 of payment name
 * @property {string} NamePaym4 10 symbols for type 4 of payment name
 * @property {number} ExchangeRate 10 symbols for exchange rate of payment type 4 in format: ####.#####
 */

/**
 * Provides information about all programmed payment types, currency name and exchange rate.
 * @return {PaymentsRes}
 */
Tremol.FP.prototype.ReadPayments = function () {
	return this.do('ReadPayments');
};

/**
 * @typedef {Object} PLUbarcodeRes
 * @property {number} PLUNum 5 symbols for article number with leading zeroes in format #####
 * @property {string} Barcode 13 symbols for article barcode
 */

/**
 * Provides information about the barcode of the specified article.
 * @param {number} PLUNum 5 symbols for article number with leading zeroes in format: #####
 * @return {PLUbarcodeRes}
 */
Tremol.FP.prototype.ReadPLUbarcode = function (PLUNum) {
	return this.do('ReadPLUbarcode', 'PLUNum', PLUNum);
};

/**
 * @typedef {Object} PLUgeneralRes
 * @property {number} PLUNum 5 symbols for article number with leading zeroes in format: #####
 * @property {string} PLUName 32 symbols for article name
 * @property {number} Price 1..10 symbols for article price
 * @property {string} FlagsPriceQty (Setting price, quantity, type of goods) 1 symbols with value: 
Flags.7=1 
Flags.6=0 
Flags.5=0 
Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) 
Flags.3=1 Yes, Flags.3=0 No (Allow negative) 
Flags.2=1 Yes, Flags.2=0 No (Monitoring quantity in stock) 
Flags.1=1 Yes, Flags.1=0 No (Free price limited) 
Flags.0=1 Yes, Flags.0=0 No (Free price enabled)
 * @property {number} BelongToDepNumber BelongToDepNo + 80h, 1 symbol for PLU department = 0x80 … 0x93
 * @property {string} AvailableQuantity Up to11 symbols for quantity in stock
 * @property {string} Barcode 13 symbols for article barcode
 * @property {string} TurnoverAmount Up to 11symbols for PLU accumulated turnover
 * @property {string} SoldQuantity Up to 11 symbols for Sales quantity of the article
 * @property {string} StornoTurnover Up to 11 symbols for accumulated Storno turnover
 * @property {string} StornoQuantity Up to 11 symbols for accumulated Storno quantiy
 * @property {number} LastZReportNumber Up to 5 symbols for the number of the last article report with zeroing
 * @property {Date} LastZReportDate 16 symbols for the date and time of the last article report with zeroing 
in format DD-MM-YYYY HH:MM
 */

/**
 * Provides information about the general registers of the specified.
 * @param {number} PLUNum 5 symbols for article number with leading zeroes in format: #####
 * @return {PLUgeneralRes}
 */
Tremol.FP.prototype.ReadPLUgeneral = function (PLUNum) {
	return this.do('ReadPLUgeneral', 'PLUNum', PLUNum);
};

/**
 * @typedef {Object} PLUpriceRes
 * @property {number} PLUNum 5 symbols for article number with leading zeroes in format #####
 * @property {number} Price 1..10 symbols for article price
 * @property {Tremol.Enums.OptionPrice} OptionPrice 1 byte for Price flag with next value: 
 - '0'- Free price is disable valid only programmed price 
 - '1'- Free price is enable 
 - '2'- Limited price
 */

/**
 * Provides information about the price and price type of the specified article.
 * @param {number} PLUNum 5 symbols for article number with leading zeroes in format: #####
 * @return {PLUpriceRes}
 */
Tremol.FP.prototype.ReadPLUprice = function (PLUNum) {
	return this.do('ReadPLUprice', 'PLUNum', PLUNum);
};

/**
 * @typedef {Object} PLUqtyRes
 * @property {number} PLUNum 5 symbols for article number with leading zeroes in format #####
 * @property {number} AvailableQuantity Up to13 symbols for quantity in stock
 * @property {Tremol.Enums.OptionQuantityType} OptionQuantityType 1 symbol for Quantity flag with next value:  
- '0'- Availability of PLU stock is not monitored  
- '1'- Disable negative quantity  
- '2'- Enable negative quantity
 */

/**
 * Provides information about the quantity registers of the specified article.
 * @param {number} PLUNum 5 symbols for article number with leading zeroes in format: #####
 * @return {PLUqtyRes}
 */
Tremol.FP.prototype.ReadPLUqty = function (PLUNum) {
	return this.do('ReadPLUqty', 'PLUNum', PLUNum);
};

/**
 * @typedef {Object} RegistrationInfoRes
 * @property {string} IDNum 13 symbols owner's ID number (ЕДБ)
 * @property {string} VATNum 15 symbols for owner's VAT registration number (ДДВ)
 * @property {string} RegistrationNumber Register number on the Fiscal device by registration
 * @property {Date} RegistrationDate Date of registration
 */

/**
 * Provides information about the owner's numbers and registration date time.
 * @return {RegistrationInfoRes}
 */
Tremol.FP.prototype.ReadRegistrationInfo = function () {
	return this.do('ReadRegistrationInfo');
};

/**
 * @typedef {Object} SerialAndFiscalNumsRes
 * @property {string} SerialNumber 11 symbols for individual number of the fiscal device
 * @property {string} FMNumber 11 symbols for individual number of the fiscal memory
 * @property {string} ECR_UniqueNum 24 symbols for ECR unique number
 */

/**
 * Provides information about the manufacturing number of the fiscal device, FM number and ECR Unique number.
 * @return {SerialAndFiscalNumsRes}
 */
Tremol.FP.prototype.ReadSerialAndFiscalNums = function () {
	return this.do('ReadSerialAndFiscalNums');
};

/**
 * Read Service mode status
 * @return {Tremol.Enums.OptionServiceMode}
 */
Tremol.FP.prototype.ReadServiceMode = function () {
	return this.do('ReadServiceMode');
};

/**
 * Read info for enable/disable short receipts
 * @return {Tremol.Enums.OptionActivationRS}
 */
Tremol.FP.prototype.ReadShortReceiptSending = function () {
	return this.do('ReadShortReceiptSending');
};

/**
 * @typedef {Object} StatusRes
 * @property {boolean} FM_Read_only FM Read only
 * @property {boolean} Power_down_in_opened_fiscal_receipt Power down in opened fiscal receipt
 * @property {boolean} Printer_not_ready_overheat Printer not ready - overheat
 * @property {boolean} DateTime_not_set DateTime not set
 * @property {boolean} DateTime_wrong DateTime wrong
 * @property {boolean} RAM_reset RAM reset
 * @property {boolean} Hardware_clock_error Hardware clock error
 * @property {boolean} Printer_not_ready_no_paper Printer not ready - no paper
 * @property {boolean} Reports_registers_Overflow Reports registers Overflow
 * @property {boolean} Blocking_after_24_hours_without_report Blocking after 24 hours without report
 * @property {boolean} Daily_report_is_not_zeroed Daily report is not zeroed
 * @property {boolean} Article_report_is_not_zeroed Article report is not zeroed
 * @property {boolean} Operator_report_is_not_zeroed Operator report is not zeroed
 * @property {boolean} Duplicate_printed Duplicate printed
 * @property {boolean} Opened_Non_fiscal_Receipt Opened Non-fiscal Receipt
 * @property {boolean} Opened_Fiscal_Receipt Opened Fiscal Receipt
 * @property {boolean} fiscal_receipt_type_1 fiscal receipt type 1
 * @property {boolean} fiscal_receipt_type_2 fiscal receipt type 2
 * @property {boolean} fiscal_receipt_type_3 fiscal receipt type 3
 * @property {boolean} SD_card_near_full SD card near full
 * @property {boolean} SD_card_full SD card full
 * @property {boolean} No_FM_module No FM module
 * @property {boolean} FM_error FM error
 * @property {boolean} FM_full FM full
 * @property {boolean} FM_near_full FM near full
 * @property {boolean} Decimal_point Decimal point (1=fract, 0=whole)
 * @property {boolean} FM_fiscalized FM fiscalized
 * @property {boolean} FM_produced FM produced
 * @property {boolean} Printer_automatic_cutting Printer: automatic cutting
 * @property {boolean} External_display_transparent_display External display: transparent display
 * @property {boolean} Missing_display Missing display
 * @property {boolean} Drawer_automatic_opening Drawer: automatic opening
 * @property {boolean} Customer_logo_included_in_the_receipt Customer logo included in the receipt
 * @property {boolean} Blocking_after_10_days_without_communication Blocking after 10 days without communication
 * @property {boolean} Wrong_SIM_card Wrong SIM card
 * @property {boolean} Wrong_SD_card Wrong SD card
 * @property {boolean} No_SIM_card No SIM card
 * @property {boolean} No_GPRS_Modem No GPRS Modem
 * @property {boolean} No_mobile_operator No mobile operator
 * @property {boolean} No_GPRS_service No GPRS service
 * @property {boolean} Near_end_of_paper Near end of paper
 */

/**
 * Provides detailed 7-byte information about the current status of the fiscal device.
 * @return {StatusRes}
 */
Tremol.FP.prototype.ReadStatus = function () {
	return this.do('ReadStatus');
};

/**
 * @typedef {Object} TotalFiscalSumsRes
 * @property {string} SumSalesTurnover 14 s. for total grand sum of sales turnover from fiscal registration
 * @property {string} SumStornoTurnover 14 s. for total sum of Storno turnover from fiscal registration
 * @property {string} SumSalesVAT 14 s. for total VAT sum of sales from fiscal registration
 * @property {string} SumStornoVAT 14 s. for total VAT sum of Storno from fiscal registration
 * @property {string} SumMacSalesTurnover 14 s. for total grand sum of maced. sales turnover from fiscal 
registration
 * @property {string} SumMacStornoTurnover 14 s. for total sum of maced.Storno turnover from fiscal 
registration
 * @property {string} SumMacSalesVAT 14 s. for total VAT sum of maced.sales from fiscal registration
 * @property {string} SumMacStornoVAT 14 s. for total VAT sum of maced.Storno from fiscal registration
 */

/**
 * Provides information about the total fiscal accumulative sums from sales and Storno
 * @return {TotalFiscalSumsRes}
 */
Tremol.FP.prototype.ReadTotalFiscalSums = function () {
	return this.do('ReadTotalFiscalSums');
};

/**
 * @typedef {Object} VATratesRes
 * @property {number} VATrate0 Value of VAT rate А from 7 symbols in format ##.##%
 * @property {number} VATrate1 Value of VAT rate Б from 7 symbols in format ##.##%
 * @property {number} VATrate2 Value of VAT rate В from 7 symbols in format ##.##%
 * @property {number} VATrate3 Value of VAT rate Г from 7 symbols in format ##.##%
 */

/**
 * Provides information about the current VAT rates which are the last values stored into the FM.
 * @return {VATratesRes}
 */
Tremol.FP.prototype.ReadVATrates = function () {
	return this.do('ReadVATrates');
};

/**
 * @typedef {Object} VersionRes
 * @property {Tremol.Enums.OptionDeviceType} OptionDeviceType 1 symbol for type of fiscal device: 
- '1'- ECR 
- '2'- FPr
 * @property {string} Model Up to 50 symbols for Model name
 * @property {string} Version Up to 20 symbols for Version name and Check sum
 */

/**
 * Provides information about the device type, model name and version.
 * @return {VersionRes}
 */
Tremol.FP.prototype.ReadVersion = function () {
	return this.do('ReadVersion');
};

/**
 * Registers cash received on account or paid out.
 * @param {number} OperNum Symbols from 1 to 20 corresponding to the operator's number
 * @param {string} OperPass 4 symbols for operator's password
 * @param {number} Amount Up to 10 symbols for the amount lodged/withdrawn
 * @param {string=} Text TextLength-2 symbols. In the beginning and in the end of line symbol '#' is 
printed.
 */
Tremol.FP.prototype.ReceivedOnAccount_PaidOut = function (OperNum, OperPass, Amount, Text) {
	return this.do('ReceivedOnAccount_PaidOut', 'OperNum', OperNum, 'OperPass', OperPass, 'Amount', Amount, 'Text', Text);
};

/**
 * Select type of display
 * @param {Tremol.Enums.OptionExternalDisplay} OptionExternalDisplay -'1' -Tremol display 
-'0' - Others
 */
Tremol.FP.prototype.SelectExternalDisplay = function (OptionExternalDisplay) {
	return this.do('SelectExternalDisplay', 'OptionExternalDisplay', OptionExternalDisplay);
};

/**
 * Register the sell of department. Correction is forbidden!
 * @param {string} NamePLU 36 symbols for name of sale. 34 symbols are printed on paper.
 * @param {number} DepNum 1 symbol for article department 
attachment, formed in the following manner: DepNum[HEX] + 80h example: 
Dep01 = 81h, Dep02 = 82h … Dep19 = 93h
 * @param {number} Price Up to 10 symbols for article's price.
 * @param {Tremol.Enums.OptionGoodsType} OptionGoodsType 1 symbol with value: 
 - '1' - macedonian goods  
 - '0' - importation
 * @param {number=} Quantity Up to 10 symbols for article's quantity sold
 * @param {number=} DiscAddP Up to 7 for percentage of discount/addition. Use minus 
sign '-' for discount
 * @param {number=} DiscAddV Up to 8 symbols for percentage of discount/addition. 
Use minus sign '-' for discount
 */
Tremol.FP.prototype.SellPLUfromDep = function (NamePLU, DepNum, Price, OptionGoodsType, Quantity, DiscAddP, DiscAddV) {
	return this.do('SellPLUfromDep', 'NamePLU', NamePLU, 'DepNum', DepNum, 'Price', Price, 'OptionGoodsType', OptionGoodsType, 'Quantity', Quantity, 'DiscAddP', DiscAddP, 'DiscAddV', DiscAddV);
};

/**
 * Register the sell with specified quantity of article from the internal FD database. Correction is forbidden!
 * @param {Tremol.Enums.OptionSign} OptionSign 1 symbol with optional value: 
 - '+' -Sale
 * @param {number} PLUNum 5 symbols for PLU number of FD's database in format #####
 * @param {number=} Price Up to 10 symbols for sale price
 * @param {number=} Quantity Up to 10 symbols for article's quantity sold
 * @param {number=} DiscAddP Up to 7 for percentage of discount/addition. Use minus 
sign '-' for discount
 * @param {number=} DiscAddV Up to 8 symbolsfor percentage of discount/addition. 
Use minus sign '-' for discount
 */
Tremol.FP.prototype.SellPLUFromFD_DB = function (OptionSign, PLUNum, Price, Quantity, DiscAddP, DiscAddV) {
	return this.do('SellPLUFromFD_DB', 'OptionSign', OptionSign, 'PLUNum', PLUNum, 'Price', Price, 'Quantity', Quantity, 'DiscAddP', DiscAddP, 'DiscAddV', DiscAddV);
};

/**
 * Register the sell of article with specified name, price, quantity, VAT class and/or discount/addition on the transaction. Correction is forbidden!
 * @param {string} NamePLU 36 symbols for article's name
 * @param {Tremol.Enums.OptionVATClass} OptionVATClass 1 character for VAT class: 
 - 'А' - VAT Class 0 
 - 'Б' - VAT Class 1 
 - 'В' - VAT Class 2 
 - 'Г' - VAT Class 3
 * @param {number} Price Up to 10 symbols for article's price.
 * @param {Tremol.Enums.OptionGoodsType} OptionGoodsType 1 symbol with value: 
 - '1' - macedonian goods  
 - '0' - importation
 * @param {number=} Quantity Up to 10 symbols for quantity
 * @param {number=} DiscAddP Up to 7 symbols for percentage of discount/addition. 
Use minus sign '-' for discount
 * @param {number=} DiscAddV Up to 8 symbols for value of discount/addition. 
Use minus sign '-' for discount
 */
Tremol.FP.prototype.SellPLUwithSpecifiedVAT = function (NamePLU, OptionVATClass, Price, OptionGoodsType, Quantity, DiscAddP, DiscAddV) {
	return this.do('SellPLUwithSpecifiedVAT', 'NamePLU', NamePLU, 'OptionVATClass', OptionVATClass, 'Price', Price, 'OptionGoodsType', OptionGoodsType, 'Quantity', Quantity, 'DiscAddP', DiscAddP, 'DiscAddV', DiscAddV);
};

/**
 * Stores in the memory the graphic file under stated number. Prints information about loaded in the printer graphic files.
 * @param {string} LogoNumber 1 character value from '0' to '9' or '?'. The number sets the active logo 
number, and the '?' invokes only printing of information
 */
Tremol.FP.prototype.SetActiveLogo = function (LogoNumber) {
	return this.do('SetActiveLogo', 'LogoNumber', LogoNumber);
};

/**
 * Sets the date and time and prints out the current values.
 * @param {Date} DateTime Date Time parameter in format: DD-MM-YY HH:MM:SS
 */
Tremol.FP.prototype.SetDateTime = function (DateTime) {
	return this.do('SetDateTime', 'DateTime', DateTime);
};

/**
 * Stores the VAT and ID numbers into the operative memory.
 * @param {string} Password 6 symbols string
 * @param {string} IDNum 13 symbols owner's ID number
 * @param {string} VATNum 15 symbols for owner's VAT number
 */
Tremol.FP.prototype.SetIDandVATnum = function (Password, IDNum, VATNum) {
	return this.do('SetIDandVATnum', 'Password', Password, 'IDNum', IDNum, 'VATNum', VATNum);
};

/**
 * Calculate the subtotal amount with printing and display visualization options. Provide information about values of the calculated amounts. If a percent or value discount/addition has been specified the subtotal and the discount/addition value will be printed regardless the parameter for printing.
 * @param {Tremol.Enums.OptionPrinting} OptionPrinting 1 symbol with value: 
 - '1' - Yes 
 - '0' - No
 * @param {Tremol.Enums.OptionDisplay} OptionDisplay 1 symbol with value: 
 - '1' - Yes 
 - '0' - No
 * @param {number=} DiscAddV Up to 8 symbols for the value of the 
discount/addition. Use minus sign '-' for discount
 * @param {number=} DiscAddP Up to 7 symbols for the percentage value of the 
discount/addition. Use minus sign '-' for discount
 * @return {number}
 */
Tremol.FP.prototype.Subtotal = function (OptionPrinting, OptionDisplay, DiscAddV, DiscAddP) {
	return this.do('Subtotal', 'OptionPrinting', OptionPrinting, 'OptionDisplay', OptionDisplay, 'DiscAddV', DiscAddV, 'DiscAddP', DiscAddP);
};

/**
* Sends client definitions to the server for compatibillity.
*/
Tremol.FP.prototype.ApplyClientLibraryDefinitions = function () {
	var defs = '<Defs><ServerStartupSettings>  <Encoding CodePage="1251" EncodingName="Cyrillic (Windows)" />  <GenerationTimeStamp>2011061631</GenerationTimeStamp>  <SignalFD>0</SignalFD>  <SilentFindDevice>0</SilentFindDevice>  <EM>0</EM> </ServerStartupSettings><Command Name="CashDrawerOpen" CmdByte="0x2A"><FPOperation>Opens the cash drawer.</FPOperation></Command><Command Name="CashPayCloseReceipt" CmdByte="0x36"><FPOperation>Paying the exact amount in cash and close the fiscal receipt.</FPOperation></Command><Command Name="ClearDisplay" CmdByte="0x24"><FPOperation>Clears the external display.</FPOperation></Command><Command Name="CloseNonFiscReceipt" CmdByte="0x2F"><FPOperation>Closes the non-fiscal receipt.</FPOperation></Command><Command Name="CloseReceipt" CmdByte="0x38"><FPOperation>Close the fiscal receipt (Fiscal receipt, Storno receipt, or Non-fical receipt). When the payment is finished.</FPOperation></Command><Command Name="ConfirmIDNumandVATnum" CmdByte="0x41"><FPOperation>Confirm storing VAT and ID numbers into the operative memory.</FPOperation><Args><Arg Name="Password" Value="" Type="Text" MaxLen="6"><Desc>6 symbols string</Desc></Arg><Arg Name="" Value="2" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <Password[6]> <;> <\'2\'> ]]></ArgsFormatRaw></Args></Command><Command Name="CutPaper" CmdByte="0x29"><FPOperation>Start paper cutter. The command works only in fiscal printer devices.</FPOperation></Command><Command Name="DirectCommand" CmdByte="0xF1"><FPOperation>Executes the direct command .</FPOperation><Args><Arg Name="Input" Value="" Type="Text" MaxLen="200"><Desc>Raw request to FP</Desc></Arg></Args><Response ACK="false"><Res Name="Output" Value="" Type="Text" MaxLen="200"><Desc>FP raw response</Desc></Res></Response></Command><Command Name="DisplayDateTime" CmdByte="0x28"><FPOperation>Shows the current date and time on the external display.</FPOperation></Command><Command Name="DisplayTextLine1" CmdByte="0x25"><FPOperation>Shows a 20-symbols text in the upper external display line.</FPOperation><Args><Arg Name="Text" Value="" Type="Text" MaxLen="20"><Desc>20 symbols text</Desc></Arg><ArgsFormatRaw><![CDATA[ <Text[20]> ]]></ArgsFormatRaw></Args></Command><Command Name="DisplayTextLine2" CmdByte="0x26"><FPOperation>Shows a 20-symbols text in the lower external display line.</FPOperation><Args><Arg Name="Text" Value="" Type="Text" MaxLen="20"><Desc>20 symbols text</Desc></Arg><ArgsFormatRaw><![CDATA[ <Text[20]> ]]></ArgsFormatRaw></Args></Command><Command Name="DisplayTextLines1and2" CmdByte="0x27"><FPOperation>Shows a 20-symbols text in the first line and last 20-symbols text in the second line of the external display lines.</FPOperation><Args><Arg Name="Text" Value="" Type="Text" MaxLen="40"><Desc>40 symbols text</Desc></Arg><ArgsFormatRaw><![CDATA[ <Text[40]> ]]></ArgsFormatRaw></Args></Command><Command Name="EnterServiceMode" CmdByte="0x5A"><FPOperation>Enter Service mode</FPOperation><Args><Arg Name="Option" Value="S" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Option" Value="W" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OptionServiceMode" Value="" Type="Option" MaxLen="1"><Options><Option Name="Sales mode" Value="0" /><Option Name="Service mode" Value="1" /></Options><Desc>1 symbol:  -\'1\' - Service mode -\'0\' - Sales mode</Desc></Arg><Arg Name="ServicePassword" Value="" Type="Text" MaxLen="8"><Desc>8 ASCII symbols</Desc></Arg><ArgsFormatRaw><![CDATA[ <Option[\'S\']> <;> <Option[\'W\']> <;><ServiceMode[1]><;> <ServicePassword[8]> ]]></ArgsFormatRaw></Args></Command><Command Name="ManageDetailedReceiptInfoSending" CmdByte="0x5A"><FPOperation>Temporary enable/disable detailed receipts info sending</FPOperation><Args><Arg Name="Option1" Value="D" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Option2" Value="W" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OptionActivationRS" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol of value - \'1\' - Yes - \'0\' - No</Desc></Arg><ArgsFormatRaw><![CDATA[ <Option1[\'D\']> <;> <Option2[\'W\']> <;> <ActivationRS[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="ManageShortReceiptSending" CmdByte="0x5A"><FPOperation>Temporary enable/disable short receipts sending</FPOperation><Args><Arg Name="Option1" Value="F" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Option2" Value="W" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OptionActivationRS" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol with value : - \'1\' - Yes - \'0\' - No</Desc></Arg><ArgsFormatRaw><![CDATA[ <Option1[\'F\']> <;> <Option2[\'W\']> <;> <ActivationRS[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="OpenNonFiscalReceipt" CmdByte="0x2E"><FPOperation>Opens a non-fiscal receipt assigned to the specified operator</FPOperation><Args><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from \'1\' to \'20\' corresponding to operator\'s number</Desc></Arg><Arg Name="OperPass" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for operator\'s password</Desc></Arg><ArgsFormatRaw><![CDATA[ < OperNum[1..2]> <;> < OperPass[4]> ]]></ArgsFormatRaw></Args></Command><Command Name="OpenReceiptOrStorno" CmdByte="0x30"><FPOperation>Opens a fiscal receipt assigned to the specified operator</FPOperation><Args><Arg Name="OperNum" Value="1" Type="Decimal" MaxLen="2"><Desc>Symbol from 1 to 20 corresponding to operator\'s number</Desc></Arg><Arg Name="OperPass" Value="0" Type="Text" MaxLen="4"><Desc>4 symbols for operator\'s password</Desc></Arg><Arg Name="OptionReceiptType" Value="1" Type="Option" MaxLen="1"><Options><Option Name="Sale" Value="1" /><Option Name="Storno" Value="0" /></Options><Desc>1 symbol with value:  - \'1\' - Sale  - \'0\' - Storno</Desc></Arg><Arg Name="reserved" Value="0" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OptionPrintType" Value="0" Type="Option" MaxLen="1"><Options><Option Name="Postponed printing" Value="2" /><Option Name="Step by step printing" Value="0" /></Options><Desc>1 symbol with value  - \'0\' - Step by step printing  - \'2\' - Postponed printing</Desc></Arg><ArgsFormatRaw><![CDATA[ <OperNum[1..2]> <;> <OperPass[4]> <;> < ReceiptType[1]> <;> <reserved[\'0\']> <;> <PrintType[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="PaperFeed" CmdByte="0x2B"><FPOperation>Feeds one line of paper.</FPOperation></Command><Command Name="PayExactSum" CmdByte="0x35"><FPOperation>Register the payment in the receipt with specified type of payment and exact amount received.</FPOperation><Args><Arg Name="OptionPaymentType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Card" Value="1" /><Option Name="Cash" Value="0" /><Option Name="Credit" Value="3" /><Option Name="Currency" Value="4" /><Option Name="Voucher" Value="2" /></Options><Desc>1 symbol with values  - \'0\' - Cash  - \'1\' - Card  - \'2\' - Voucher  - \'3\' - Credit  - \'4\' - Currency</Desc></Arg><Arg Name="reserved" Value="0" Type="OptionHardcoded" MaxLen="1" /><Arg Name="reserved" Value="&quot;" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <PaymentType[1]> <;> <reserved[\'0\']> <;><reserved[\'"\']> ]]></ArgsFormatRaw></Args></Command><Command Name="Payment" CmdByte="0x35"><FPOperation>Registers the payment in the receipt with specified type of payment and amount received.</FPOperation><Args><Arg Name="OptionPaymentType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Card" Value="1" /><Option Name="Cash" Value="0" /><Option Name="Credit" Value="3" /><Option Name="Currency" Value="4" /><Option Name="Voucher" Value="2" /></Options><Desc>1 symbol with values  - \'0\' - Cash  - \'1\' - Card  - \'2\' - Voucher  - \'3\' - Credit  - \'4\' - Currency</Desc></Arg><Arg Name="OptionChange" Value="" Type="Option" MaxLen="1"><Options><Option Name="With Change" Value="0" /><Option Name="Without Change" Value="1" /></Options><Desc>Default value is 0, 1 symbol with value:  - \'0 - With Change  - \'1\' - Without Change</Desc></Arg><Arg Name="Amount" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 characters for received amount</Desc></Arg><Arg Name="OptionChangeType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Change In Cash" Value="0" /><Option Name="Change In Currency" Value="2" /><Option Name="Same As The payment" Value="1" /></Options><Desc>1 symbols with value:  - \'0\' - Change In Cash  - \'1\' - Same As The payment  - \'2\' - Change In Currency</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="*" /></Arg><ArgsFormatRaw><![CDATA[ <PaymentType[1]> <;> <OptionChange[1]> <;> <Amount[1..10]> { <*> <OptionChangeType[1]> } ]]></ArgsFormatRaw></Args></Command><Command Name="PrintArticleReport" CmdByte="0x7E"><FPOperation>Prints an article report with or without zeroing (\'Z\' or \'X\').</FPOperation><Args><Arg Name="OptionZeroing" Value="" Type="Option" MaxLen="1"><Options><Option Name="Without zeroing" Value="X" /><Option Name="Zeroing" Value="Z" /></Options><Desc>with following values:  - \'Z\' - Zeroing  - \'X\' - Without zeroing</Desc></Arg><ArgsFormatRaw><![CDATA[ <OptionZeroing[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintBarcode" CmdByte="0x51"><FPOperation>Prints barcode from type stated by CodeType and CodeLen and with data stated in CodeData field.</FPOperation><Args><Arg Name="" Value="P" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OptionCodeType" Value="" Type="Option" MaxLen="1"><Options><Option Name="CODABAR" Value="6" /><Option Name="CODE 128" Value="I" /><Option Name="CODE 39" Value="4" /><Option Name="CODE 93" Value="H" /><Option Name="EAN 13" Value="2" /><Option Name="EAN 8" Value="3" /><Option Name="ITF" Value="5" /><Option Name="UPC A" Value="0" /><Option Name="UPC E" Value="1" /></Options><Desc>1 symbol with possible values:  - \'0\' - UPC A  - \'1\' - UPC E  - \'2\' - EAN 13  - \'3\' - EAN 8  - \'4\' - CODE 39  - \'5\' - ITF  - \'6\' - CODABAR  - \'H\' - CODE 93  - \'I\' - CODE 128</Desc></Arg><Arg Name="CodeLen" Value="" Type="Decimal" MaxLen="2"><Desc>1..2 bytes for number of bytes according to the table</Desc></Arg><Arg Name="CodeData" Value="" Type="Text" MaxLen="100"><Desc>From 0 to 255 bytes data in range according to the table</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'P\'> <;> <CodeType[1]> <;> <CodeLen[1..2]> <;> <CodeData[100]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintBriefFMReportByDate" CmdByte="0x7B"><FPOperation>Print a brief FM report by initial and end date.</FPOperation><Args><Arg Name="StartDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for initial date in the DDMMYY format</Desc></Arg><Arg Name="EndDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for final date in the DDMMYY format</Desc></Arg><ArgsFormatRaw><![CDATA[ <StartDate "DDMMYY"><;><EndDate "DDMMYY"> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintBriefFMReportByNum" CmdByte="0x79"><FPOperation>Print a brief FM report by initial and end FM report number.</FPOperation><Args><Arg Name="StartNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for the initial FM report number included in report, format ####</Desc></Arg><Arg Name="EndNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for the final FM report number included in report, format ####</Desc></Arg><ArgsFormatRaw><![CDATA[ <StartNum[4]><;><EndNum[4]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintDailyReport" CmdByte="0x7C"><FPOperation>Depending on the parameter prints: − daily fiscal report with zeroing and fiscal memory record, preceded by Electronic Journal report print (\'Z\'); − daily fiscal report without zeroing (\'X\');</FPOperation><Args><Arg Name="OptionZeroing" Value="" Type="Option" MaxLen="1"><Options><Option Name="Without zeroing" Value="X" /><Option Name="Zeroing" Value="Z" /></Options><Desc>1 character with following values:  - \'Z\' - Zeroing  - \'X\' - Without zeroing</Desc></Arg><ArgsFormatRaw><![CDATA[ <OptionZeroing[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintDepartmentReport" CmdByte="0x76"><FPOperation>Print a department report with or without zeroing (\'Z\' or \'X\').</FPOperation><Args><Arg Name="OptionZeroing" Value="" Type="Option" MaxLen="1"><Options><Option Name="Without zeroing" Value="X" /><Option Name="Zeroing" Value="Z" /></Options><Desc>1 symbol with value:  - \'Z\' - Zeroing  - \'X\' - Without zeroing</Desc></Arg><ArgsFormatRaw><![CDATA[ <OptionZeroing[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintDetailedFMReportByDate" CmdByte="0x7A"><FPOperation>Prints a detailed FM report by initial and end date.</FPOperation><Args><Arg Name="StartDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for initial date in the DDMMYY format</Desc></Arg><Arg Name="EndDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for final date in the DDMMYY format</Desc></Arg><ArgsFormatRaw><![CDATA[ <StartDate "DDMMYY"><;><EndDate "DDMMYY"> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintDetailedFMReportByNum" CmdByte="0x78"><FPOperation>Print a detailed FM report by initial and end FM report number.</FPOperation><Args><Arg Name="StartNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for the initial report number included in report, format ####</Desc></Arg><Arg Name="EndNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for the final report number included in report, format ####</Desc></Arg><ArgsFormatRaw><![CDATA[ <StartNum[4]><;><EndNum[4]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintDiagnostics" CmdByte="0x22"><FPOperation>Prints out a diagnostic receipt.</FPOperation></Command><Command Name="PrintEJ" CmdByte="0x7C"><FPOperation>Print or store Electronic Journal report with all documents.</FPOperation><Args><Arg Name="" Value="J1" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="*" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'J1\'> <;> <\'*\'> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintEJByDate" CmdByte="0x7C"><FPOperation>Printing Electronic Journal Report from Report initial date to report Final date.</FPOperation><Args><Arg Name="" Value="J1" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="D" Type="OptionHardcoded" MaxLen="1" /><Arg Name="StartRepFromDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for initial date in the DDMMYY format</Desc></Arg><Arg Name="EndRepFromDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for final date in the DDMMYY format</Desc></Arg><ArgsFormatRaw><![CDATA[<\'J1\'> <;> <\'D\'> <;> <StartRepFromDate"DDMMYY"> <;> <EndRepFromDate"DDMMYY"> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintEJByReceiptNumFromZrep" CmdByte="0x7C"><FPOperation>Printing Electronic Journal Report from receipt number to receipt number.</FPOperation><Args><Arg Name="" Value="J1" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="N" Type="OptionHardcoded" MaxLen="1" /><Arg Name="ZrepNum" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for Z report number</Desc></Arg><Arg Name="StartReceiptNum" Value="" Type="Decimal_with_format" MaxLen="6" Format="000000 for initial receipt number"><Desc>5 symbols in format ###### for initial receipt number included in report.</Desc></Arg><Arg Name="EndReceiptNum" Value="" Type="Decimal_with_format" MaxLen="6" Format="000000 for final receipt number included"><Desc>5 symbols in format ###### for final receipt number included in report.</Desc></Arg><ArgsFormatRaw><![CDATA[<\'J1\'><;><\'N\'><;><ZrepNum[4]><;> <StartReceiptNum[6]><;><EndReceiptNum[6]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintEJByStornoNumFromZrep" CmdByte="0x7C"><FPOperation>Printing Electronic Journal Report from receipt number to receipt number.</FPOperation><Args><Arg Name="" Value="J1" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="n" Type="OptionHardcoded" MaxLen="1" /><Arg Name="ZrepNum" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for Z report number</Desc></Arg><Arg Name="StartReceiptNum" Value="" Type="Text" MaxLen="6"><Desc>5 symbols for initial daily Storno receipt number</Desc></Arg><Arg Name="EndReceiptNum" Value="" Type="Text" MaxLen="6"><Desc>5 symbols for final daily Storno receipt number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'J1\'><;><\'n\'><;><ZrepNum[4]><;><StartReceiptNum[6]> <;><EndReceiptNum[6]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintEJByZBlocks" CmdByte="0x7C"><FPOperation>Print or store Electronic Journal Report from by number of Z report blocks.</FPOperation><Args><Arg Name="" Value="J1" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="Z" Type="OptionHardcoded" MaxLen="1" /><Arg Name="StartZNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for initial number report in format ####</Desc></Arg><Arg Name="EndZNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for final number report in format ####</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'J1\'> <;> <\'Z\'> <;> <StartZNum[4]> <;> <EndZNum[4]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintLogo" CmdByte="0x6C"><FPOperation>Prints the programmed graphical logo with the stated number.</FPOperation><Args><Arg Name="Number" Value="" Type="Decimal" MaxLen="2"><Desc>Number of logo to be printed. If missing prints logo with number 0</Desc></Arg><ArgsFormatRaw><![CDATA[ <Number[1..2]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintOperatorReport" CmdByte="0x7D"><FPOperation>Prints an operator\'s report for a specified operator (0 = all operators) with or without zeroing (\'Z\' or \'X\'). When a \'Z\' value is specified the report should include all operators.</FPOperation><Args><Arg Name="OptionZeroing" Value="" Type="Option" MaxLen="1"><Options><Option Name="Without zeroing" Value="X" /><Option Name="Zeroing" Value="Z" /></Options><Desc>with following values:  - \'Z\' - Zeroing  - \'X\' - Without zeroing</Desc></Arg><Arg Name="Number" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 0 to 20corresponding to operator\'s number ,0 for all operators</Desc></Arg><ArgsFormatRaw><![CDATA[ <OptionZeroing[1]> <;> <Number[1..2]> ]]></ArgsFormatRaw></Args></Command><Command Name="PrintSpecialEventsFMreport" CmdByte="0x77"><FPOperation>Print whole special FM events report.</FPOperation></Command><Command Name="PrintText" CmdByte="0x37"><FPOperation>Print a free text. The command can be executed only if receipt is opened (Fiscal receipt, Storno receipt or Non-fical receipt). In the beginning and in the end of line symbol \'#\' is printed.</FPOperation><Args><Arg Name="Text" Value="" Type="Text" MaxLen="64"><Desc>TextLength-2 symbols</Desc></Arg><ArgsFormatRaw><![CDATA[ <Text[TextLength-2]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgDecimalPointPosition" CmdByte="0x43"><FPOperation>Stores a block containing the number format into the fiscal memory. Print the current status on the printer.</FPOperation><Args><Arg Name="Password" Value="" Type="Text" MaxLen="6"><Desc>6-symbols string</Desc></Arg><Arg Name="OptionDecimalPointPosition" Value="" Type="Option" MaxLen="1"><Options><Option Name="Fractions" Value="2" /><Option Name="Whole numbers" Value="0" /></Options><Desc>1 symbol with values:  - \'0\'- Whole numbers  - \'2\' - Fractions</Desc></Arg><ArgsFormatRaw><![CDATA[ <Password[6]> <;> <DecimalPointPosition[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgDepartment" CmdByte="0x47"><FPOperation>Set data for the state department number from the internal FD database.</FPOperation><Args><Arg Name="Number" Value="" Type="Decimal_with_format" MaxLen="2" Format="00"><Desc>2 symbols department number in format ##</Desc></Arg><Arg Name="Name" Value="" Type="Text" MaxLen="23"><Desc>23 characters department name</Desc></Arg><Arg Name="OptionVATClass" Value="" Type="Option" MaxLen="1"><Options><Option Name="VAT Class 0" Value="А" /><Option Name="VAT Class 1" Value="Б" /><Option Name="VAT Class 2" Value="В" /><Option Name="VAT Class 3" Value="Г" /></Options><Desc>1 character for VAT class:  - \'А\' - VAT Class 0  - \'Б\' - VAT Class 1  - \'В\' - VAT Class 2  - \'Г\' - VAT Class 3</Desc></Arg><Arg Name="Price" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for department price</Desc></Arg><Arg Name="FlagsPrice" Value="" Type="Flags" MaxLen="1"><Desc>1 symbol with value: Flags.7=1 Flags.6=0 Flags.5=0 Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) Flags.3=0 Flags.2=1 Yes, Flags.2=0 No (Single Transaction) Flags.1=1 Yes, Flags.1=0 No (Free price limited) Flags.0=1 Yes, Flags.0=0 No (Free price enabled)</Desc></Arg><ArgsFormatRaw><![CDATA[ <Number[2]> <;> <Name[23]> <;> <OptionVATClass[1]> <;> <Price[1..10]> <;> <FlagsPrice[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgDisplayGreetingMessage" CmdByte="0x49"><FPOperation>Program the contents of a Display Greeting message.</FPOperation><Args><Arg Name="" Value="0" Type="OptionHardcoded" MaxLen="1" /><Arg Name="DisplayGreetingText" Value="" Type="Text" MaxLen="20"><Desc>20 symbols for Display greeting message</Desc></Arg><ArgsFormatRaw><![CDATA[<\'0\'> <;> <DisplayGreetingText[20]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgExtDisplay" CmdByte="0x46"><FPOperation>Programs the external display.</FPOperation><Args><Arg Name="Password" Value="" Type="Text" MaxLen="6"><Desc>A 6-symbol string</Desc></Arg><ArgsFormatRaw><![CDATA[ <Password[6]> <NumBytesCom1line[1]> <Com1line[8]> <NumBytesCom2line[1]> <Com2Line[8]> < NumBytesClrDis[1]> <ComClrDis[8]> <NumbytesXtrCom[1]> <ComXtrCom[1]> <FlagPrecod[1]> {<PrecodTabl[64]>} ]]></ArgsFormatRaw></Args></Command><Command Name="ProgFooter" CmdByte="0x49"><FPOperation>Program the contents of a footer lines.</FPOperation><Args><Arg Name="OptionFooterLine" Value="" Type="Option" MaxLen="2"><Options><Option Name="Footer 1" Value="F1" /><Option Name="Footer 2" Value="F2" /><Option Name="Footer 3" Value="F3" /></Options><Desc>2 symbol with value: -\'F1\' - Footer 1 -\'F2\' - Footer 2 -\'F3\' - Footer 3</Desc></Arg><Arg Name="FooterText" Value="" Type="Text" MaxLen="64"><Desc>TextLength symbols for footer line</Desc></Arg><ArgsFormatRaw><![CDATA[<OptionFooterLine[2]> <;> <FooterText[TextLength]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgHeader" CmdByte="0x49"><FPOperation>Program the contents of a header lines.</FPOperation><Args><Arg Name="OptionHeaderLine" Value="" Type="Option" MaxLen="1"><Options><Option Name="Header 1" Value="1" /><Option Name="Header 2" Value="2" /><Option Name="Header 3" Value="3" /><Option Name="Header 4" Value="4" /><Option Name="Header 5" Value="5" /><Option Name="Header 6" Value="6" /><Option Name="ID number" Value="7" /><Option Name="VAT number" Value="8" /></Options><Desc>1 symbol with value:  - \'1\' - Header 1  - \'2\' - Header 2  - \'3\' - Header 3  - \'4\' - Header 4  - \'5\' - Header 5  - \'6\' - Header 6  - \'7\' - ID number  - \'8\' - VAT number</Desc></Arg><Arg Name="HeaderText" Value="" Type="Text" MaxLen="64"><Desc>TextLength symbols for header lines</Desc></Arg><ArgsFormatRaw><![CDATA[<OptionHeaderLine[1]> <;> <HeaderText[TextLength]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgOperator" CmdByte="0x4A"><FPOperation>Programs the operator\'s name and password.</FPOperation><Args><Arg Name="Number" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from \'1\' to \'20\' corresponding to operator\'s number</Desc></Arg><Arg Name="Name" Value="" Type="Text" MaxLen="20"><Desc>20 symbols for operator\'s name</Desc></Arg><Arg Name="Password" Value="" Type="Text" MaxLen="6"><Desc>6 symbols for operator\'s password</Desc></Arg><ArgsFormatRaw><![CDATA[ <Number[1..2]> <;> <Name[20]> <;> <Password[6]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgParameters" CmdByte="0x45"><FPOperation>Programs the number of POS, printing of logo, cash drawer opening, cutting permission, external display management mode, article report type, enable or disable currency in receipt and working operators counter.</FPOperation><Args><Arg Name="POSNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for number of POS in format ####</Desc></Arg><Arg Name="OptionPrintLogo" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Arg><Arg Name="OptionAutoOpenDrawer" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Arg><Arg Name="OptionAutoCut" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Arg><Arg Name="OptionExternalDispManagement" Value="" Type="Option" MaxLen="1"><Options><Option Name="Auto" Value="0" /><Option Name="Manual" Value="1" /></Options><Desc>1 symbol of value:  - \'1\' - Manual  - \'0\' - Auto</Desc></Arg><Arg Name="OptionArticleReportType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Brief" Value="0" /><Option Name="Detailed" Value="1" /></Options><Desc>1 symbol of value:  - \'1\' - Detailed  - \'0\' - Brief</Desc></Arg><Arg Name="OptionEnableCurrency" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Arg><Arg Name="OptionWorkOperatorCount" Value="" Type="Option" MaxLen="1"><Options><Option Name="More" Value="0" /><Option Name="One" Value="1" /></Options><Desc>1 symbol of value:  - \'1\' - One  - \'0\' - More</Desc></Arg><ArgsFormatRaw><![CDATA[ <POSNum[4]> <;> <PrintLogo[1]> <;> <AutoOpenDrawer[1]> <;> <AutoCut[1]> <;> <ExternalDispManagement[1]> <;> <ArticleReportType[1]> <;> <EnableCurrency[1]> <;> <WorkOperatorCount[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgPayment" CmdByte="0x44"><FPOperation>Program the name of the payment types.</FPOperation><Args><Arg Name="OptionPaymentNum" Value="" Type="Option" MaxLen="1"><Options><Option Name="Payment 1" Value="1" /><Option Name="Payment 2" Value="2" /><Option Name="Payment 3" Value="3" /><Option Name="Payment 4" Value="4" /></Options><Desc>1 symbol for payment type:  - \'1\' - Payment 1  - \'2\' - Payment 2  - \'3\' - Payment 3  - \'4\' - Payment 4</Desc></Arg><Arg Name="Name" Value="" Type="Text" MaxLen="10"><Desc>10 symbols for payment type name</Desc></Arg><Arg Name="Rate" Value="" Type="Decimal_with_format" MaxLen="10" Format="0000.00000"><Desc>10 symbols for exchange rate in format: ####.#####  of the 4 th payment type.</Desc><Meta MinLen="10" Compulsory="false" ValIndicatingPresence=";" /></Arg><ArgsFormatRaw><![CDATA[ <PaymentNum[1]> <;> <Name[10]> { <;> <Rate[10]> } ]]></ArgsFormatRaw></Args></Command><Command Name="ProgPLUbarcode" CmdByte="0x4B"><FPOperation>Program the Barcode number for a certain article (item) from the internal database.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number in format: #####</Desc></Arg><Arg Name="Option" Value="3" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Barcode" Value="" Type="Text" MaxLen="13"><Desc>13 symbols for barcode</Desc></Arg><ArgsFormatRaw><![CDATA[ <PLUNum[5]><;><Option[\'3\']><;><Barcode[13]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgPLUgeneral" CmdByte="0x4B"><FPOperation>Programs the general data for a certain article in the internal FD database. The price may have variable length, while the name field is fixed.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Text" MaxLen="5"><Desc>5 symbols for article number</Desc></Arg><Arg Name="Option" Value="1" Type="OptionHardcoded" MaxLen="1" /><Arg Name="PLUName" Value="" Type="Text" MaxLen="32"><Desc>32 symbols for article name</Desc></Arg><Arg Name="Price" Value="" Type="Decimal" MaxLen="10"><Desc>1 to 10 symbols for article price</Desc></Arg><Arg Name="FlagsPriceQty" Value="" Type="Flags" MaxLen="1"><Desc>1 symbols with value: Flags.7=1 Flags.6=0 Flags.5=0 Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) Flags.3=1 Yes, Flags.3=0 No (Allow negative quantity) Flags.2=1 Yes, Flags.2=0 No (Monitoring quantity in stock) Flags.1=1 Yes, Flags.1=0 No (Free price limited) Flags.0=1 Yes, Flags.0=0 No (Free price enabled)</Desc></Arg><Arg Name="BelongToDepNum" Value="" Type="Decimal_plus_80h" MaxLen="2"><Desc>BelongToDepNum + 80h, 1 symbol for article department attachment, formed in the following manner: BelongToDepNum[HEX] + 80h example: Dep01 = 81h, Dep02 = 82h … Dep19 = 93h</Desc></Arg><Arg Name="AvailableQuantity" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for quantity in stock</Desc></Arg><Arg Name="Barcode" Value="" Type="Text" MaxLen="13"><Desc>13 symbols for barcode</Desc></Arg><ArgsFormatRaw><![CDATA[ <PLUNum[5]> <;> <Option[\'1\']> <;> <PLUName[32]> <;> <Price[1..10]> <;> <FlagsPriceQty[1]> <;> <BelongToDepNum[1..2]> <;> <AvailableQuantity[1..11]> <;> <Barcode[13]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgPLUprice" CmdByte="0x4B"><FPOperation>Program the price for a certain article from the internal database.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number in format: #####</Desc></Arg><Arg Name="Option" Value="4" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Price" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for article price</Desc></Arg><Arg Name="OptionPrice" Value="" Type="Option" MaxLen="1"><Options><Option Name="Free price is disable valid only programmed price" Value="0" /><Option Name="Free price is enable" Value="1" /><Option Name="Limited price" Value="2" /></Options><Desc>1 byte for Price flag with next value:  - \'0\'- Free price is disable valid only programmed price  - \'1\'- Free price is enable  - \'2\'- Limited price</Desc></Arg><ArgsFormatRaw><![CDATA[ <PLUNum[5]> <;> <Option[\'4\']> <;> <Price[1..10]> <;> <OptionPrice[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgPLUqty" CmdByte="0x4B"><FPOperation>Programs available quantity and quantiy type for a certain article in the internal database.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number in format: #####</Desc></Arg><Arg Name="Option" Value="2" Type="OptionHardcoded" MaxLen="1" /><Arg Name="AvailableQuantity" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for quantity in stock</Desc></Arg><Arg Name="OptionQuantityType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Availability of PLU stock is not monitored" Value="0" /><Option Name="Disable negative quantity" Value="1" /><Option Name="Enable negative quantity" Value="2" /></Options><Desc>1 symbol for Quantity flag with next value:  - \'0\'- Availability of PLU stock is not monitored  - \'1\'- Disable negative quantity  - \'2\'- Enable negative quantity</Desc></Arg><ArgsFormatRaw><![CDATA[<PLUNum[5]><;><Option[\'2\']><;><AvailableQuantity [1..11]> <;> <OptionQuantityType[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="ProgVATrates" CmdByte="0x42"><FPOperation>Stores a block containing the values of the VAT rates into the fiscal memory. Print the values on the printer.</FPOperation><Args><Arg Name="Password" Value="" Type="Text" MaxLen="6"><Desc>6 symbols string</Desc></Arg><Arg Name="VATrate1" Value="" Type="Decimal_with_format" MaxLen="6" Format="00.00"><Desc>Value of VAT rate А from 6 symbols in format ##.##</Desc></Arg><Arg Name="VATrate2" Value="" Type="Decimal_with_format" MaxLen="6" Format="00.00"><Desc>Value of VAT rate Б from 6 symbols in format ##.##</Desc></Arg><Arg Name="VATrate3" Value="" Type="Decimal_with_format" MaxLen="6" Format="00.00"><Desc>Value of VAT rate В from 6 symbols in format ##.##</Desc></Arg><Arg Name="VATrate4" Value="" Type="Decimal_with_format" MaxLen="6" Format="00.00"><Desc>Value of VAT rate Г from 6 symbols in format ##.##</Desc></Arg><ArgsFormatRaw><![CDATA[ <Password[6]> <;> <VATrate1[6]> <;> <VATrate2[6]> <;> <VATrate3[6]> <;> <VATrate4[6]> ]]></ArgsFormatRaw></Args></Command><Command Name="RawRead" CmdByte="0xFF"><FPOperation> Reads raw bytes from FP.</FPOperation><Args><Arg Name="Count" Value="" Type="Decimal" MaxLen="5"><Desc>How many bytes to read if EndChar is not specified</Desc></Arg><Arg Name="EndChar" Value="" Type="Text" MaxLen="1"><Desc>The character marking the end of the data. If present Count parameter is ignored.</Desc></Arg></Args><Response ACK="false"><Res Name="Bytes" Value="" Type="Base64" MaxLen="100000"><Desc>FP raw response in BASE64 encoded string</Desc></Res></Response></Command><Command Name="RawWrite" CmdByte="0xFE"><FPOperation> Writes raw bytes to FP </FPOperation><Args><Arg Name="Bytes" Value="" Type="Base64" MaxLen="5000"><Desc>The bytes in BASE64 ecoded string to be written to FP</Desc></Arg></Args></Command><Command Name="ReadCurrentRecInfo" CmdByte="0x72"><FPOperation>Read the current status of the receipt.</FPOperation><Response ACK="false"><Res Name="OptionIsReceiptOpened" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol with value:  - \'0\' - No  - \'1\' - Yes</Desc></Res><Res Name="OptionReceiptType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Sale" Value="1" /><Option Name="Storno" Value="0" /></Options><Desc>1 symbol with value:  - \'1\' - Sale  - \'0\' - Storno</Desc></Res><Res Name="SalesNumber" Value="" Type="Text" MaxLen="3"><Desc>3 symbols for number of sales</Desc></Res><Res Name="MacSubtotalVATG0" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from Macedonian goods by VAT groups</Desc></Res><Res Name="MacSubtotalVATG1" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from Macedonian goods by VAT groups</Desc></Res><Res Name="MacSubtotalVATG2" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from Macedonian goods by VAT groups</Desc></Res><Res Name="MacSubtotalVATG3" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from Macedonian goods by VAT groups</Desc></Res><Res Name="ImpSubtotalVATG0" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from imported goods by VAT groups</Desc></Res><Res Name="ImpSubtotalVATG1" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from imported goods by VAT groups</Desc></Res><Res Name="ImpSubtotalVATG2" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from imported goods by VAT groups</Desc></Res><Res Name="ImpSubtotalVATG3" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for subtotal from imported goods by VAT groups</Desc></Res><Res Name="OptionInitiatedPayment" Value="" Type="Option" MaxLen="1"><Options><Option Name="initiated payment" Value="1" /><Option Name="not initiated payment" Value="0" /></Options><Desc>1 symbol with value:  - \'1\' - initiated payment  - \'0\' - not initiated payment</Desc></Res><Res Name="OptionFinalizedPayment" Value="" Type="Option" MaxLen="1"><Options><Option Name="finalized payment" Value="1" /><Option Name="not finalized payment" Value="0" /></Options><Desc>1 symbol with value:  - \'1\' - finalized payment  - \'0\' - not finalized payment</Desc></Res><Res Name="OptionPowerDownInReceipt" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol with value: - \'0\' - No - \'1\' - Yes</Desc></Res><Res Name="ChangeAmount" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols the amount of the due change in the stated payment type</Desc></Res><Res Name="OptionChangeType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Change In Cash" Value="0" /><Option Name="Change In Currency" Value="2" /><Option Name="Same As The payment" Value="1" /></Options><Desc>1 symbols with value:  - \'0\' - Change In Cash  - \'1\' - Same As The payment  - \'2\' - Change In Currency</Desc></Res><ResFormatRaw><![CDATA[<IsReceiptOpened[1]> <;> <ReceiptType[1]><;><SalesNumber[3]> <;> <MacSubtotalVATG0[11]> <;> <MacSubtotalVATG1[11]> <;> < MacSubtotalVATG2[11]> <;> <MacSubtotalVATG3[11]> <;> <ImpSubtotalVATG0[11]> <;> <ImpSubtotalVATG1[11]> <;> <ImpSubtotalVATG2[11]> <;> <ImpSubtotalVATG3[11]> <;> <InitiatedPayment[1]> <;> <FinalizedPayment[1]> <;> < PowerDownInReceipt [1]> <;> <ChangeAmount[1..11]> <;> <OptionChangeType[1]]]></ResFormatRaw></Response></Command><Command Name="ReadDailyCounters" CmdByte="0x6E"><FPOperation>Provides information about the total fiscal counters and last Z- report date and time.</FPOperation><Args><Arg Name="" Value="5" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'5\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="5" Type="OptionHardcoded" MaxLen="1" /><Res Name="TotalReciepts" Value="" Type="Decimal" MaxLen="5"><Desc>5 symbols for total number of fiscal receipts</Desc></Res><Res Name="TotalStorno" Value="" Type="Decimal" MaxLen="5"><Desc>5 symbols for total number of Storno receipts</Desc></Res><Res Name="NumLastFMBlock" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for number of the last FM report</Desc></Res><Res Name="NumEJ" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for number of EJ</Desc></Res><Res Name="DateTime" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yyyy HH:mm"><Desc>16 symbols for date and time of the last block storage in FM in format "DD-MM-YYYY HH:MM"</Desc></Res><ResFormatRaw><![CDATA[<\'5\'> <;> <TotalReciepts[1..5]> <;> <TotalStorno[1..5]> <;> <NumLastFMBlock[1..5]> <;> <NumEJ[1..5]> <;> <DateTime "DD-MM-YYYY HH:MM">]]></ResFormatRaw></Response></Command><Command Name="ReadDailyCountersByOperator" CmdByte="0x6F"><FPOperation>Read the last operator\'s report number and date and time.</FPOperation><Args><Arg Name="" Value="5" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'5\'> <;> <OperNum[1..2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="5" Type="OptionHardcoded" MaxLen="1" /><Res Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Res><Res Name="WorkOperatorsCounter" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for number of the work operators</Desc></Res><Res Name="LastOperatorReportDateTime" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yyyy HH:mm"><Desc>16 symbols for date and time of the last operator\'s report in format DD-MM-YYYY HH:MM</Desc></Res><ResFormatRaw><![CDATA[<\'5\'> <;> <OperNum[1..2]> <;> <WorkOperatorsCounter[1..5]> <;> <LastOperatorReportDateTime "DD-MM-YYYY HH:MM">]]></ResFormatRaw></Response></Command><Command Name="ReadDailyGeneralRegistersByOperator" CmdByte="0x6F"><FPOperation>Read the total number of customers, discounts, additions, corrections and accumulated amounts by specified operator.</FPOperation><Args><Arg Name="" Value="1" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'1\'><;><OperNum[1..2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="1" Type="OptionHardcoded" MaxLen="1" /><Res Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Res><Res Name="FiscalReciept" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for daily number of fiscal receipts</Desc></Res><Res Name="StornoReciept" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for daily number of Storno receipts</Desc></Res><Res Name="DiscountsNum" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for number of discounts</Desc></Res><Res Name="DiscountsAmount" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for accumulated amount of discounts</Desc></Res><Res Name="AdditionsNum" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for number of additions</Desc></Res><Res Name="AdditionsAmount" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for accumulated amount of additions</Desc></Res><ResFormatRaw><![CDATA[<\'1\'><;><OperNum[1..2]> <;> < FiscalReciept [1..5]> <;> < StornoReciept[1..5]> <;> <DiscountsNum[1..5]> <;> <DiscountsAmount[1..11]> <;> <AdditionsNum[1..5]> <;> <AdditionsAmount[1..11]> <;>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyPO" CmdByte="0x6E"><FPOperation>Provides information about the PO amounts by type of payment and the total number of operations.</FPOperation><Args><Arg Name="" Value="3" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'3\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="3" Type="OptionHardcoded" MaxLen="1" /><Res Name="AmountPayment" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for PO amount by type of payment</Desc></Res><Res Name="NumPO" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for the total number of operations</Desc></Res><ResFormatRaw><![CDATA[<\'3\'> <;> <AmountPayment[1..11]> <;> <NumPO[1..5]> <;>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyPObyOperator" CmdByte="0x6F"><FPOperation>Provides information about the PO and the total number of operations by specified operator.</FPOperation><Args><Arg Name="" Value="3" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'3\'> <;> <OperNum[1..2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="3" Type="OptionHardcoded" MaxLen="1" /><Res Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Res><Res Name="AmountPO_Payments" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for the PO by type of payment</Desc></Res><Res Name="NumPO" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for the total number of operations</Desc></Res><ResFormatRaw><![CDATA[<\'3\'> <;> <OperNum[1..2]> <;> <AmountPO_Payments[1..11]> <;> <NumPO[1..5]>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyRA" CmdByte="0x6E"><FPOperation>Provides information about the RA amounts by type of payment and the total number of operations.</FPOperation><Args><Arg Name="" Value="2" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'2\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="2" Type="OptionHardcoded" MaxLen="1" /><Res Name="AmountPayment" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for RA amounts</Desc></Res><Res Name="NumRA" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for the total number of operations</Desc></Res><ResFormatRaw><![CDATA[<\'2\'> <;> <AmountPayment[1..11]> <;> <NumRA[1..5]>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyRAbyOperator" CmdByte="0x6F"><FPOperation>Provides information about the RA and the total number of operations by specified operator.</FPOperation><Args><Arg Name="" Value="2" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'2\'> <;> <OperNum[1..2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="2" Type="OptionHardcoded" MaxLen="1" /><Res Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Res><Res Name="AmountRA_Payments" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for the RA by type of payment</Desc></Res><Res Name="NumRA" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for the total number of operations</Desc></Res><ResFormatRaw><![CDATA[<\'2\'> <;> <OperNum[1..2]> <;> <AmountRA_Payments[1..11]> <;> <NumRA[1..5]>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyReceivedSalesAmounts" CmdByte="0x6E"><FPOperation>Provides information about the amounts received from sales and Storno change.</FPOperation><Args><Arg Name="" Value="4" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'4\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="4" Type="OptionHardcoded" MaxLen="1" /><Res Name="AmountPayment" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by cash</Desc></Res><Res Name="AmountPaymentOthers" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by others payment</Desc></Res><ResFormatRaw><![CDATA[<\'4\'> <;> <AmountPayment[1..11]> <;> <AmountPaymentOthers[1..11]>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyReceivedSalesAmountsByOperator" CmdByte="0x6F"><FPOperation>Read the amounts received from sales by type of payment and specified operator.</FPOperation><Args><Arg Name="" Value="4" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'4\'> <;> <OperNum[1..2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="4" Type="OptionHardcoded" MaxLen="1" /><Res Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Res><Res Name="AmountPayment" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by cash</Desc></Res><Res Name="AmountPaymentOthers" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by others payment</Desc></Res><ResFormatRaw><![CDATA[<\'4\'> <;> <OperNum[1..2]> <;> <AmountPayment[1..11]> <;> <AmountPaymentOthers[1..11]>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyReturned" CmdByte="0x6E"><FPOperation>Provides information about the amounts returned as Storno or sales change.</FPOperation><Args><Arg Name="" Value="6" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'6\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="6" Type="OptionHardcoded" MaxLen="1" /><Res Name="AmountPayment" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by cash</Desc></Res><Res Name="AmountPaymentOthers" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by others payment</Desc></Res><ResFormatRaw><![CDATA[<\'6\'> <;> <AmountPayment[1..11]> <;> <AmountPaymentOthers[1..11]>]]></ResFormatRaw></Response></Command><Command Name="ReadDailyReturnedAmounts" CmdByte="0x6F"><FPOperation>Read information about the amounts returned</FPOperation><Args><Arg Name="" Value="6" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'6\'> <;> <OperNum[1..2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="6" Type="OptionHardcoded" MaxLen="1" /><Res Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to operator\'s number</Desc></Res><Res Name="AmountPayment" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by cash</Desc></Res><Res Name="AmountPaymentOthers" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for amount received from sales or Storno change by others payment</Desc></Res><ResFormatRaw><![CDATA[<\'6\'> <;> <OperNum[1..2]> <;> <AmountPayment[1..11]> <;> <AmountPaymentOthers[1..11]>]]></ResFormatRaw></Response></Command><Command Name="ReadDailySaleAndStornoAmountsByVAT" CmdByte="0x6D"><FPOperation>Provides information about the accumulated amount by VAT group.</FPOperation><Response ACK="false"><Res Name="SalesAmountVATGr0" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from sales by VAT group А</Desc></Res><Res Name="SalesAmountVATGr1" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from sales by VAT group Б</Desc></Res><Res Name="SalesAmountVATGr2" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from sales by VAT group В</Desc></Res><Res Name="SalesAmountVATGr3" Value="" Type="Text" MaxLen="1"><Desc>Up to 11 symbols for the amount accumulated from sales by VAT group Г</Desc></Res><Res Name="SalesMacAmountVATGr0" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the mac amount accumulated from sales by</Desc></Res><Res Name="SalesMacAmountVATGr1" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the mac amount accumulated from sales by</Desc></Res><Res Name="SalesMacAmountVATGr2" Value="" Type="Text" MaxLen="1"><Desc>Up to 11 symbols for the mac amount accumulated from sales by</Desc></Res><Res Name="SalesMacAmountVATGr3" Value="" Type="Text" MaxLen="1"><Desc>Up to 11 symbols for the mac amount accumulated from sales by</Desc></Res><Res Name="StornoAmountVATGr0" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Storno by VAT group А</Desc></Res><Res Name="StornoAmountVATGr1" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Storno by VAT group Б</Desc></Res><Res Name="StornoAmountVATGr2" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Storno by VAT group В</Desc></Res><Res Name="StornoAmountVATGr3" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Storno by VAT group Г</Desc></Res><Res Name="StornoMacAmountVATGr0" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Mac Storno by</Desc></Res><Res Name="StornoMacAmountVATGr1" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Mac Storno by</Desc></Res><Res Name="StornoMacAmountVATGr2" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Mac Storno by</Desc></Res><Res Name="StornoMacAmountVATGr3" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for the amount accumulated from Mac Storno by</Desc></Res><ResFormatRaw><![CDATA[<SalesAmountVATGr0[11]> <;> <SalesAmountVATGr1[11]> <;> <SalesAmountVATGr2[11]> <;> <SalesAmountVATGr3[1]> <;> <SalesMacAmountVATGr0[11]> <;> <SalesMacAmountVATGr1[11]> <;> <SalesMacAmountVATGr2[1]> <;> <SalesMacAmountVATGr3[1]> <;> <StornoAmountVATGr0[11]> <;> < StornoAmountVATGr1[11]> <;> <StornoAmountVATGr2[11]> <;> <StornoAmountVATGr3[11]> <;> <StornoMacAmountVATGr0[11]> <;> <StornoMacAmountVATGr1[11]> <;> <StornoMacAmountVATGr2[11]> <;> <StornoMacAmountVATGr3[11]>]]></ResFormatRaw></Response></Command><Command Name="ReadDateTime" CmdByte="0x68"><FPOperation>Provides information about the current date and time.</FPOperation><Response ACK="false"><Res Name="DateTime" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yyyy HH:mm"><Desc>Date Time parameter in format: DD-MM-YY [Space] HH:MM</Desc></Res><ResFormatRaw><![CDATA[<DateTime "DD-MM-YYYY HH:MM">]]></ResFormatRaw></Response></Command><Command Name="ReadDecimalPoint" CmdByte="0x63"><FPOperation>Provides information about the current (the last value stored into the FM) decimal point format.</FPOperation><Response ACK="false"><Res Name="OptionDecimalPointPosition" Value="" Type="Option" MaxLen="1"><Options><Option Name="Fractions" Value="2" /><Option Name="Whole numbers" Value="0" /></Options><Desc>1 symbol with values:  - \'0\'- Whole numbers  - \'2\' - Fractions</Desc></Res><ResFormatRaw><![CDATA[<DecimalPointPosition[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadDepartment" CmdByte="0x67"><FPOperation>Provides information for the programmed data, the turnover from the stated department number</FPOperation><Args><Arg Name="DepNum" Value="" Type="Decimal_with_format" MaxLen="2" Format="00"><Desc>2 symbols for deparment number in format: ##</Desc></Arg><ArgsFormatRaw><![CDATA[ <DepNum[2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="DepNum" Value="" Type="Decimal_with_format" MaxLen="2" Format="00"><Desc>2 symbols for department number in format ##</Desc></Res><Res Name="DepName" Value="" Type="Text" MaxLen="32"><Desc>34 symbols for department name</Desc></Res><Res Name="OptionVATClass" Value="" Type="Option" MaxLen="1"><Options><Option Name="VAT Class 0" Value="А" /><Option Name="VAT Class 1" Value="Б" /><Option Name="VAT Class 2" Value="В" /><Option Name="VAT Class 3" Value="Г" /></Options><Desc>1 character for VAT class attachment of the department:  - \'А\' - VAT Class 0  - \'Б\' - VAT Class 1  - \'В\' - VAT Class 2  - \'Г\' - VAT Class 3</Desc></Res><Res Name="Price" Value="" Type="Decimal" MaxLen="11"><Desc>1..11 symbols for Department price</Desc></Res><Res Name="FlagsPrice" Value="" Type="Flags" MaxLen="1"><Desc>(Setting price, signle transaction, type of goods) 1 symbol with value: Flags.7=1 Flags.6=0 Flags.5=0 Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) Flags.3=0 Flags.2=1 Yes, Flags.2=0 No (Single Transaction) Flags.1=1 Yes, Flags.1=0 No (Free price limited) Flags.0=1 Yes, Flags.0=0 No (Free price enabled)</Desc></Res><Res Name="Turnover" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for accumulated turnover of the department</Desc></Res><Res Name="SoldQuantity" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for sold quantity of the department</Desc></Res><Res Name="TurnoverMac" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for maced. turnover of the department</Desc></Res><Res Name="SoldQuantityMac" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for maced. sold quantity of the department</Desc></Res><Res Name="TurnoverSt" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for Storno turnover of the department</Desc></Res><Res Name="SoldQuantitySt" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for Storno</Desc></Res><Res Name="TurnoverStMac" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for Storno maced.turnover by this department</Desc></Res><Res Name="SoldQuantityStMac" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for Storno maced quantity</Desc></Res><Res Name="LastZReportNumber" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>Up to 5 symbols for the number of last Z report in format #####</Desc></Res><Res Name="LastZReportDate" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yyyy HH:mm"><Desc>16 symbols for the date and hour in last Z report</Desc></Res><ResFormatRaw><![CDATA[<DepNum[2]> <;> <DepName[32]> <;> <OptionVATClass[1]> <;> <Price[1..11]> <;> <FlagsPrice[1]> <;> <Turnover[1..11]> <;> <SoldQuantity[1..11]> <;> <TurnoverMac[1..11]> <;> <SoldQuantityMac[1..11]> <;> <TurnoverSt[1..11]><;> <SoldQuantitySt[1..11]> <;> <TurnoverStMac[1..11]> <;> <SoldQuantityStMac[1..11]> <;> <LastZReportNumber[1..5]> <;> <LastZReportDate"DD-MM-YYYY HH:MM">]]></ResFormatRaw></Response></Command><Command Name="ReadDetailedReceiptInfoSending" CmdByte="0x5A"><FPOperation>Read info for enable/disable detailed receipts</FPOperation><Args><Arg Name="Option" Value="D" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Option" Value="R" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <Option[\'D\']> <;> <Option[\'R\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="Option" Value="ZD" Type="OptionHardcoded" MaxLen="1" /><Res Name="OptionActivationRS" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol with value : - \'1\' - Yes - \'0\' - No</Desc></Res><ResFormatRaw><![CDATA[<Option[\'ZD\']> <;> <ActivationRS[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadDisplayGreetingMessage" CmdByte="0x69"><FPOperation>Provide information about the display greeting message.</FPOperation><Args><Arg Name="" Value="0" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'0\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="0" Type="OptionHardcoded" MaxLen="1" /><Res Name="DisplayGreetingText" Value="" Type="Text" MaxLen="20"><Desc>20 symbols for greeting message</Desc></Res><ResFormatRaw><![CDATA[<\'0\'> <;> <DisplayGreetingText[20]>]]></ResFormatRaw></Response></Command><Command Name="ReadEJ" CmdByte="0x7C"><FPOperation>Read Electronic Journal report with all documents.</FPOperation><Args><Arg Name="" Value="J0" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="*" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'J0\'> <;> <\'*\'> ]]></ArgsFormatRaw></Args><Response ACK="true" ACK_PLUS="true" /></Command><Command Name="ReadEJByDate" CmdByte="0x7C"><FPOperation>Read Electronic Journal Report from Report initial date to report Final date.</FPOperation><Args><Arg Name="" Value="J0" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="D" Type="OptionHardcoded" MaxLen="1" /><Arg Name="StartRepFromDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for initial date in the DDMMYY format</Desc></Arg><Arg Name="EndRepFromDate" Value="" Type="DateTime" MaxLen="10" Format="ddMMyy"><Desc>6 symbols for final date in the DDMMYY format</Desc></Arg><ArgsFormatRaw><![CDATA[<\'J0\'> <;> <\'D\'> <;> <StartRepFromDate"DDMMYY"> <;> <EndRepFromDate"DDMMYY"> ]]></ArgsFormatRaw></Args><Response ACK="true" ACK_PLUS="true" /></Command><Command Name="ReadEJByReceiptNumFromZrep" CmdByte="0x7C"><FPOperation>Read Electronic Journal Report from receipt number to receipt number.</FPOperation><Args><Arg Name="" Value="J0" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="N" Type="OptionHardcoded" MaxLen="1" /><Arg Name="ZrepNum" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for Z report number</Desc></Arg><Arg Name="StartReceiptNum" Value="" Type="Decimal_with_format" MaxLen="6" Format="000000 for initial receipt number"><Desc>5 symbols in format ###### for initial receipt number included in report.</Desc></Arg><Arg Name="EndReceiptNum" Value="" Type="Decimal_with_format" MaxLen="6" Format="000000 for final receipt number"><Desc>5 symbols in format ###### for final receipt number included in report.</Desc></Arg><ArgsFormatRaw><![CDATA[<\'J0\'><;><\'N\'><;><ZrepNum[4]><;> <StartReceiptNum[6]><;><EndReceiptNum[6]> ]]></ArgsFormatRaw></Args><Response ACK="true" ACK_PLUS="true" /></Command><Command Name="ReadEJByStornoNumFromZrep" CmdByte="0x7C"><FPOperation>Read Electronic Journal Report from receipt number to receipt number.</FPOperation><Args><Arg Name="" Value="J0" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="n" Type="OptionHardcoded" MaxLen="1" /><Arg Name="ZrepNum" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for Z report number</Desc></Arg><Arg Name="StartReceiptNum" Value="" Type="Text" MaxLen="6"><Desc>5 symbols for initial daily Storno receipt number</Desc></Arg><Arg Name="EndReceiptNum" Value="" Type="Text" MaxLen="6"><Desc>5 symbols for final daily Storno receipt number</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'J0\'><;><\'n\'><;><ZrepNum[4]><;><StartReceiptNum[6]> <;><EndReceiptNum[6]> ]]></ArgsFormatRaw></Args><Response ACK="true" ACK_PLUS="true" /></Command><Command Name="ReadEJByZBlocks" CmdByte="0x7C"><FPOperation>Read Electronic Journal Report from by number of Z report blocks.</FPOperation><Args><Arg Name="" Value="J0" Type="OptionHardcoded" MaxLen="2" /><Arg Name="" Value="Z" Type="OptionHardcoded" MaxLen="1" /><Arg Name="StartZNum" Value="0007" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for initial number report in format ####</Desc></Arg><Arg Name="EndZNum" Value="0007" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>4 symbols for final number report in format ####</Desc></Arg><ArgsFormatRaw><![CDATA[ <\'J0\'> <;> <\'Z\'> <;> <StartZNum[4]> <;> <EndZNum[4]> ]]></ArgsFormatRaw></Args><Response ACK="true" ACK_PLUS="true" /></Command><Command Name="ReadExternalDisplay" CmdByte="0x57"><FPOperation>Select type of display</FPOperation><Args><Arg Name="Option" Value="E" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <Option[\'E\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="Option" Value="E" Type="OptionHardcoded" MaxLen="1" /><Res Name="OptionExternalType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Others" Value="0" /><Option Name="Tremol display" Value="1" /></Options><Desc>1 symbol with value:  -\'1\' -Tremol display  -\'0\' - Others</Desc></Res><ResFormatRaw><![CDATA[<Option[\'E\']> <;> <ExternalType[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadFMcontent" CmdByte="0x75"><FPOperation>Provides consequently information about every single block stored in the FM starting with Acknowledgements and ending with end message.</FPOperation><Response ACK="true" ACK_PLUS="true" /></Command><Command Name="ReadFMfreeRecords" CmdByte="0x74"><FPOperation>Read the number of the remaining free records for Z-report in the Fiscal Memory.</FPOperation><Response ACK="false"><Res Name="FreeFMrecords" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for the number of free records for Z-report in the FM</Desc></Res><ResFormatRaw><![CDATA[<FreeFMrecords[4]>]]></ResFormatRaw></Response></Command><Command Name="ReadFooter" CmdByte="0x69"><FPOperation>Provides the content of the footer lines.</FPOperation><Args><Arg Name="OptionFooterLine" Value="" Type="Option" MaxLen="2"><Options><Option Name="Footer 1" Value="F1" /><Option Name="Footer 2" Value="F2" /><Option Name="Footer 3" Value="F3" /></Options><Desc>1 symbol with value:  - \'F1\' - Footer 1  - \'F2\' - Footer 2  - \'F3\' - Footer 3</Desc></Arg><ArgsFormatRaw><![CDATA[ <OptionFooterLine[2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="OptionFooterLine" Value="" Type="Option" MaxLen="2"><Options><Option Name="Footer 1" Value="F1" /><Option Name="Footer 2" Value="F2" /><Option Name="Footer 3" Value="F3" /></Options><Desc>(Line Number)1 symbol with value:  - \'F1\' - Footer 1  - \'F2\' - Footer 2  - \'F3\' - Footer 3</Desc></Res><Res Name="FooterText" Value="" Type="Text" MaxLen="64"><Desc>TextLength symbols for footer line</Desc></Res><ResFormatRaw><![CDATA[<OptionFooterLine[2]> <;> <FooterText[TextLength]>]]></ResFormatRaw></Response></Command><Command Name="ReadGeneralDailyRegisters" CmdByte="0x6E"><FPOperation>Provides information about the number of customers (number of fiscal receipt issued), number of discounts, additions and corrections made and the accumulated amounts.</FPOperation><Args><Arg Name="" Value="1" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'1\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="1" Type="OptionHardcoded" MaxLen="1" /><Res Name="FiscalReciept" Value="" Type="Decimal" MaxLen="5"><Desc>1..5 symbols for daily number of fiscal receipts</Desc></Res><Res Name="StornoReciept" Value="" Type="Decimal" MaxLen="5"><Desc>1..5 symbols for daily number of Storno receipts</Desc></Res><Res Name="DiscountsNum" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for number of discounts</Desc></Res><Res Name="DiscountsAmount" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for accumulated amount of discounts</Desc></Res><Res Name="AdditionsNum" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for number of additions</Desc></Res><Res Name="AdditionsAmount" Value="" Type="Decimal" MaxLen="11"><Desc>Up to 11 symbols for accumulated amount of additions</Desc></Res><ResFormatRaw><![CDATA[<\'1\'> <;> < FiscalReciept [1..5]> <;> < StornoReciept[1..5]> <;> <DiscountsNum[1..5]> <;> <DiscountsAmount[1..11]> <;> <AdditionsNum[1..5]> <;> <AdditionsAmount[1..11]> <;>]]></ResFormatRaw></Response></Command><Command Name="ReadHeader" CmdByte="0x69"><FPOperation>Provides the content of the header lines.</FPOperation><Args><Arg Name="OptionHeaderLine" Value="" Type="Option" MaxLen="1"><Options><Option Name="Header 1" Value="1" /><Option Name="Header 2" Value="2" /><Option Name="Header 3" Value="3" /><Option Name="Header 4" Value="4" /><Option Name="Header 5" Value="5" /><Option Name="Header 6" Value="6" /><Option Name="ID number" Value="7" /><Option Name="VAT number" Value="8" /></Options><Desc>1 byte with value:  - \'1\' - Header 1  - \'2\' - Header 2  - \'3\' - Header 3  - \'4\' - Header 4  - \'5\' - Header 5  - \'6\' - Header 6  - \'7\' - ID number  - \'8\' - VAT number</Desc></Arg><ArgsFormatRaw><![CDATA[ <OptionHeaderLine[1]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="OptionHeaderLine" Value="" Type="Option" MaxLen="1"><Options><Option Name="Header 1" Value="1" /><Option Name="Header 2" Value="2" /><Option Name="Header 3" Value="3" /><Option Name="Header 4" Value="4" /><Option Name="Header 5" Value="5" /><Option Name="Header 6" Value="6" /><Option Name="ID number" Value="7" /><Option Name="VAT number" Value="8" /></Options><Desc>(Line Number)1 byte with value:  - \'1\' - Header 1  - \'2\' - Header 2  - \'3\' - Header 3  - \'4\' - Header 4  - \'5\' - Header 5  - \'6\' - Header 6  - \'7\' - ID number  - \'8\' - VAT number</Desc></Res><Res Name="HeaderText" Value="" Type="Text" MaxLen="64"><Desc>TextLength symbols</Desc></Res><ResFormatRaw><![CDATA[<OptionHeaderLine[1]> <;><HeaderText[TextLength]>]]></ResFormatRaw></Response></Command><Command Name="ReadLastDailyReportInfo" CmdByte="0x73"><FPOperation>Read date and number of last Z-report and last RAM reset event.</FPOperation><Response ACK="false"><Res Name="LastZDailyReportDate" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yyyy"><Desc>10 symbols for last Z-report date in DD-MM-YYYY format</Desc></Res><Res Name="LastZDailyReportNum" Value="" Type="Decimal" MaxLen="4"><Desc>Up to 4 symbols for the number of the last daily report</Desc></Res><Res Name="LastRAMResetNum" Value="" Type="Decimal" MaxLen="4"><Desc>Up to 4 symbols for the number of the last RAM reset</Desc></Res><ResFormatRaw><![CDATA[<LastZDailyReportDate "DD-MM-YYYY"> <;> <LastZDailyReportNum[1..4]> <;> <LastRAMResetNum[1..4]>]]></ResFormatRaw></Response></Command><Command Name="ReadLastReceiptNum" CmdByte="0x71"><FPOperation>Provides information about the number of the last issued receipt.</FPOperation><Response ACK="false"><Res Name="LastReceiptNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000 for the number of last issued fiscal receipt"><Desc>Up to 4 symbols in format #### for the number of last issued fiscal receipt</Desc></Res><Res Name="LastStornoNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000 for the number of last issued Storno receipt"><Desc>Up to 4 symbols in format #### for the number of last issued Storno receipt</Desc></Res><ResFormatRaw><![CDATA[<LastReceiptNum[1..4]> <;> <LastStornoNum[1..4]>]]></ResFormatRaw></Response></Command><Command Name="ReadOperatorNamePassword" CmdByte="0x6A"><FPOperation>Provides information about an operator\'s name and password.</FPOperation><Args><Arg Name="Number" Value="" Type="Decimal" MaxLen="2"><Desc>Symbol from 1 to 20 corresponding to the number of operator</Desc></Arg><ArgsFormatRaw><![CDATA[ <Number[1..2]> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="Number" Value="" Type="Decimal" MaxLen="2"><Desc>Symbol from 1 to 20 corresponding to the number of operator</Desc></Res><Res Name="Name" Value="" Type="Text" MaxLen="20"><Desc>20 symbols for operator\'s name</Desc></Res><Res Name="Password" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for operator\'s password</Desc></Res><ResFormatRaw><![CDATA[<Number[1..2]> <;> <Name[20]> <;> <Password[4]>]]></ResFormatRaw></Response></Command><Command Name="ReadParameters" CmdByte="0x65"><FPOperation>Provides information about the programmed number of POS and the current values of the logo, cutting permission, display mode, enable/disable currency in receipt.</FPOperation><Response ACK="false"><Res Name="POSNum" Value="" Type="Decimal_with_format" MaxLen="4" Format="0000"><Desc>(POS Number) 4 symbols for number of POS in format ####</Desc></Res><Res Name="OptionPrintLogo" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>(Print Logo) 1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Res><Res Name="OptionAutoOpenDrawer" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>(Auto Open Drawer) 1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Res><Res Name="OptionAutoCut" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>(Auto Cut) 1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Res><Res Name="OptionExternalDispManagement" Value="" Type="Option" MaxLen="1"><Options><Option Name="Auto" Value="0" /><Option Name="Manual" Value="1" /></Options><Desc>(External Display Management) 1 symbol of value:  - \'1\' - Manual  - \'0\' - Auto</Desc></Res><Res Name="OptionRecieptSend" Value="" Type="Option" MaxLen="1"><Options><Option Name="automatic sending" Value="1" /><Option Name="without sending" Value="0" /></Options><Desc>1 symbol of value: - \'1\' - automatic sending - \'0\' - without sending</Desc></Res><Res Name="OptionEnableCurrency" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>(Enable Currency) 1 symbol of value:  - \'1\' - Yes  - \'0\' - No</Desc></Res><Res Name="OptionWorkOperatorCount" Value="" Type="Option" MaxLen="1"><Options><Option Name="More" Value="0" /><Option Name="One" Value="1" /></Options><Desc>(Work Operator Count) 1 symbol of value:  - \'1\' - One  - \'0\' - More</Desc></Res><ResFormatRaw><![CDATA[<POSNum[4]> <;> <PrintLogo[1]> <;> <AutoOpenDrawer[1]> <;> <AutoCut[1]> <;> <ExternalDispManagement[1]> <;><RecieptSend[1]> <;> <EnableCurrency[1]> <;> <WorkOperatorCount[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadPayments" CmdByte="0x64"><FPOperation>Provides information about all programmed payment types, currency name and exchange rate.</FPOperation><Response ACK="false"><Res Name="NamePaym0" Value="" Type="Text" MaxLen="10"><Desc>10 symbols for type 0 of payment name</Desc></Res><Res Name="NamePaym1" Value="" Type="Text" MaxLen="10"><Desc>10 symbols for type 1 of payment name</Desc></Res><Res Name="NamePaym2" Value="" Type="Text" MaxLen="10"><Desc>10 symbols for type 2 of payment name</Desc></Res><Res Name="NamePaym3" Value="" Type="Text" MaxLen="10"><Desc>10 symbols for type 3 of payment name</Desc></Res><Res Name="NamePaym4" Value="" Type="Text" MaxLen="10"><Desc>10 symbols for type 4 of payment name</Desc></Res><Res Name="ExchangeRate" Value="" Type="Decimal_with_format" MaxLen="10" Format="0000.00000"><Desc>10 symbols for exchange rate of payment type 4 in format: ####.#####</Desc></Res><ResFormatRaw><![CDATA[<NamePaym0[10]> <;> <NamePaym1[10]> <;> <NamePaym2[10]> <;> <NamePaym3[10]> <;> <NamePaym4[10]> <;> <ExchangeRate[10]>]]></ResFormatRaw></Response></Command><Command Name="ReadPLUbarcode" CmdByte="0x6B"><FPOperation>Provides information about the barcode of the specified article.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format: #####</Desc></Arg><Arg Name="Option" Value="3" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <PLUNum[5]><;><Option[\'3\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format #####</Desc></Res><Res Name="Option" Value="3" Type="OptionHardcoded" MaxLen="1" /><Res Name="Barcode" Value="" Type="Text" MaxLen="13"><Desc>13 symbols for article barcode</Desc></Res><ResFormatRaw><![CDATA[<PLUNum[5]><;><Option[\'3\']><;><Barcode[13]>]]></ResFormatRaw></Response></Command><Command Name="ReadPLUgeneral" CmdByte="0x6B"><FPOperation>Provides information about the general registers of the specified.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format: #####</Desc></Arg><Arg Name="Option" Value="1" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <PLUNum[5]> <;> <Option[\'1\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format: #####</Desc></Res><Res Name="Option" Value="1" Type="OptionHardcoded" MaxLen="1" /><Res Name="PLUName" Value="" Type="Text" MaxLen="32"><Desc>32 symbols for article name</Desc></Res><Res Name="Price" Value="" Type="Decimal" MaxLen="11"><Desc>1..10 symbols for article price</Desc></Res><Res Name="FlagsPriceQty" Value="" Type="Flags" MaxLen="1"><Desc>(Setting price, quantity, type of goods) 1 symbols with value: Flags.7=1 Flags.6=0 Flags.5=0 Flags.4=1 Yes, Flags.4=0 No (Macedonian goods) Flags.3=1 Yes, Flags.3=0 No (Allow negative) Flags.2=1 Yes, Flags.2=0 No (Monitoring quantity in stock) Flags.1=1 Yes, Flags.1=0 No (Free price limited) Flags.0=1 Yes, Flags.0=0 No (Free price enabled)</Desc></Res><Res Name="BelongToDepNumber" Value="" Type="Decimal_plus_80h" MaxLen="2"><Desc>BelongToDepNo + 80h, 1 symbol for PLU department = 0x80 … 0x93</Desc></Res><Res Name="AvailableQuantity" Value="" Type="Text" MaxLen="1"><Desc>Up to11 symbols for quantity in stock</Desc></Res><Res Name="Barcode" Value="" Type="Text" MaxLen="13"><Desc>13 symbols for article barcode</Desc></Res><Res Name="TurnoverAmount" Value="" Type="Text" MaxLen="11"><Desc>Up to 11symbols for PLU accumulated turnover</Desc></Res><Res Name="SoldQuantity" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for Sales quantity of the article</Desc></Res><Res Name="StornoTurnover" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for accumulated Storno turnover</Desc></Res><Res Name="StornoQuantity" Value="" Type="Text" MaxLen="11"><Desc>Up to 11 symbols for accumulated Storno quantiy</Desc></Res><Res Name="LastZReportNumber" Value="" Type="Decimal" MaxLen="5"><Desc>Up to 5 symbols for the number of the last article report with zeroing</Desc></Res><Res Name="LastZReportDate" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yyyy HH:mm"><Desc>16 symbols for the date and time of the last article report with zeroing in format DD-MM-YYYY HH:MM</Desc></Res><ResFormatRaw><![CDATA[<PLUNum[5]> <;> <Option[\'1\']> <;> <PLUName[32]> <;> <Price[1..11]> <;> <FlagsPriceQty[1]> <;> <BelongToDepNumber[1]> <;> <AvailableQuantity[1]> <;> <Barcode[13]> <;> <TurnoverAmount[11]> <;> <SoldQuantity[11]> <;> <StornoTurnover[11]> <;> <StornoQuantity [11]> <;> <LastZReportNumber[1..5]> <;> <LastZReportDate "DD-MM-YYYY HH:MM">]]></ResFormatRaw></Response></Command><Command Name="ReadPLUprice" CmdByte="0x6B"><FPOperation>Provides information about the price and price type of the specified article.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format: #####</Desc></Arg><Arg Name="Option" Value="4" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <PLUNum[5]><;><Option[\'4\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format #####</Desc></Res><Res Name="Option" Value="4" Type="OptionHardcoded" MaxLen="1" /><Res Name="Price" Value="" Type="Decimal" MaxLen="10"><Desc>1..10 symbols for article price</Desc></Res><Res Name="OptionPrice" Value="" Type="Option" MaxLen="1"><Options><Option Name="Free price is disable valid only programmed price" Value="0" /><Option Name="Free price is enable" Value="1" /><Option Name="Limited price" Value="2" /></Options><Desc>1 byte for Price flag with next value:  - \'0\'- Free price is disable valid only programmed price  - \'1\'- Free price is enable  - \'2\'- Limited price</Desc></Res><ResFormatRaw><![CDATA[<PLUNum[5]><;><Option[\'4\']><;><Price[1..10]><;><OptionPrice[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadPLUqty" CmdByte="0x6B"><FPOperation>Provides information about the quantity registers of the specified article.</FPOperation><Args><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format: #####</Desc></Arg><Arg Name="Option" Value="2" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <PLUNum[5]> <;> <Option[\'2\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for article number with leading zeroes in format #####</Desc></Res><Res Name="Option" Value="2" Type="OptionHardcoded" MaxLen="1" /><Res Name="AvailableQuantity" Value="" Type="Decimal" MaxLen="13"><Desc>Up to13 symbols for quantity in stock</Desc></Res><Res Name="OptionQuantityType" Value="" Type="Option" MaxLen="1"><Options><Option Name="Availability of PLU stock is not monitored" Value="0" /><Option Name="Disable negative quantity" Value="1" /><Option Name="Enable negative quantity" Value="2" /></Options><Desc>1 symbol for Quantity flag with next value:  - \'0\'- Availability of PLU stock is not monitored  - \'1\'- Disable negative quantity  - \'2\'- Enable negative quantity</Desc></Res><ResFormatRaw><![CDATA[<PLUNum[5]> <;> <Option[\'2\']> <;> <AvailableQuantity[1..13]> <;> <OptionQuantityType[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadRegistrationInfo" CmdByte="0x61"><FPOperation>Provides information about the owner\'s numbers and registration date time.</FPOperation><Response ACK="false"><Res Name="IDNum" Value="" Type="Text" MaxLen="13"><Desc>13 symbols owner\'s ID number (ЕДБ)</Desc></Res><Res Name="VATNum" Value="" Type="Text" MaxLen="15"><Desc>15 symbols for owner\'s VAT registration number (ДДВ)</Desc></Res><Res Name="RegistrationNumber" Value="" Type="Text" MaxLen="6"><Desc>Register number on the Fiscal device by registration</Desc></Res><Res Name="RegistrationDate" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yyyy HH:mm"><Desc>Date of registration</Desc></Res><ResFormatRaw><![CDATA[<IDNum[13]> <;> <VATNum[15]> <;> <RegistrationNumber[6]><;> <RegistrationDate "DD-MM-YYYY HH:MM" >]]></ResFormatRaw></Response></Command><Command Name="ReadSerialAndFiscalNums" CmdByte="0x60"><FPOperation>Provides information about the manufacturing number of the fiscal device, FM number and ECR Unique number.</FPOperation><Response ACK="false"><Res Name="SerialNumber" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for individual number of the fiscal device</Desc></Res><Res Name="FMNumber" Value="" Type="Text" MaxLen="11"><Desc>11 symbols for individual number of the fiscal memory</Desc></Res><Res Name="ECR_UniqueNum" Value="" Type="Text" MaxLen="24"><Desc>24 symbols for ECR unique number</Desc></Res><ResFormatRaw><![CDATA[<SerialNumber[11]> <;> <FMNumber[11]> <;> <ECR_UniqueNum[24]>]]></ResFormatRaw></Response></Command><Command Name="ReadServiceMode" CmdByte="0x5A"><FPOperation>Read Service mode status</FPOperation><Args><Arg Name="Option" Value="S" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Option" Value="R" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <Option[\'S\']> <;> <Option[\'R\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="Option" Value="ZS" Type="OptionHardcoded" MaxLen="1" /><Res Name="OptionServiceMode" Value="" Type="Option" MaxLen="1"><Options><Option Name="Sales mode" Value="0" /><Option Name="Service mode" Value="1" /></Options><Desc>1 symbol:  -\'1\' - Service mode -\'0\' - Sales mode</Desc></Res><ResFormatRaw><![CDATA[<Option[\'ZS\']> <;> <ServiceMode[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadShortReceiptSending" CmdByte="0x5A"><FPOperation>Read info for enable/disable short receipts</FPOperation><Args><Arg Name="Option" Value="F" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Option" Value="R" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <Option[\'F\']> <;> <Option[\'R\']> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="Option" Value="ZF" Type="OptionHardcoded" MaxLen="1" /><Res Name="OptionActivationRS" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol with value : - \'1\' - Yes - \'0\' - No</Desc></Res><ResFormatRaw><![CDATA[<Option[\'ZF\']> <;> <ActivationRS[1]>]]></ResFormatRaw></Response></Command><Command Name="ReadStatus" CmdByte="0x20"><FPOperation>Provides detailed 7-byte information about the current status of the fiscal device.</FPOperation><Response ACK="false"><Res Name="FM_Read_only" Value="" Type="Status" Byte="0" Bit="0"><Desc>FM Read only</Desc></Res><Res Name="Power_down_in_opened_fiscal_receipt" Value="" Type="Status" Byte="0" Bit="1"><Desc>Power down in opened fiscal receipt</Desc></Res><Res Name="Printer_not_ready_overheat" Value="" Type="Status" Byte="0" Bit="2"><Desc>Printer not ready - overheat</Desc></Res><Res Name="DateTime_not_set" Value="" Type="Status" Byte="0" Bit="3"><Desc>DateTime not set</Desc></Res><Res Name="DateTime_wrong" Value="" Type="Status" Byte="0" Bit="4"><Desc>DateTime wrong</Desc></Res><Res Name="RAM_reset" Value="" Type="Status" Byte="0" Bit="5"><Desc>RAM reset</Desc></Res><Res Name="Hardware_clock_error" Value="" Type="Status" Byte="0" Bit="6"><Desc>Hardware clock error</Desc></Res><Res Name="Printer_not_ready_no_paper" Value="" Type="Status" Byte="1" Bit="0"><Desc>Printer not ready - no paper</Desc></Res><Res Name="Reports_registers_Overflow" Value="" Type="Status" Byte="1" Bit="1"><Desc>Reports registers Overflow</Desc></Res><Res Name="Blocking_after_24_hours_without_report" Value="" Type="Status" Byte="1" Bit="2"><Desc>Blocking after 24 hours without report</Desc></Res><Res Name="Daily_report_is_not_zeroed" Value="" Type="Status" Byte="1" Bit="3"><Desc>Daily report is not zeroed</Desc></Res><Res Name="Article_report_is_not_zeroed" Value="" Type="Status" Byte="1" Bit="4"><Desc>Article report is not zeroed</Desc></Res><Res Name="Operator_report_is_not_zeroed" Value="" Type="Status" Byte="1" Bit="5"><Desc>Operator report is not zeroed</Desc></Res><Res Name="Duplicate_printed" Value="" Type="Status" Byte="1" Bit="6"><Desc>Duplicate printed</Desc></Res><Res Name="Opened_Non_fiscal_Receipt" Value="" Type="Status" Byte="2" Bit="0"><Desc>Opened Non-fiscal Receipt</Desc></Res><Res Name="Opened_Fiscal_Receipt" Value="" Type="Status" Byte="2" Bit="1"><Desc>Opened Fiscal Receipt</Desc></Res><Res Name="fiscal_receipt_type_1" Value="" Type="Status" Byte="2" Bit="2"><Desc>fiscal receipt type 1</Desc></Res><Res Name="fiscal_receipt_type_2" Value="" Type="Status" Byte="2" Bit="3"><Desc>fiscal receipt type 2</Desc></Res><Res Name="fiscal_receipt_type_3" Value="" Type="Status" Byte="2" Bit="4"><Desc>fiscal receipt type 3</Desc></Res><Res Name="SD_card_near_full" Value="" Type="Status" Byte="2" Bit="5"><Desc>SD card near full</Desc></Res><Res Name="SD_card_full" Value="" Type="Status" Byte="2" Bit="6"><Desc>SD card full</Desc></Res><Res Name="No_FM_module" Value="" Type="Status" Byte="3" Bit="0"><Desc>No FM module</Desc></Res><Res Name="FM_error" Value="" Type="Status" Byte="3" Bit="1"><Desc>FM error</Desc></Res><Res Name="FM_full" Value="" Type="Status" Byte="3" Bit="2"><Desc>FM full</Desc></Res><Res Name="FM_near_full" Value="" Type="Status" Byte="3" Bit="3"><Desc>FM near full</Desc></Res><Res Name="Decimal_point" Value="" Type="Status" Byte="3" Bit="4"><Desc>Decimal point (1=fract, 0=whole)</Desc></Res><Res Name="FM_fiscalized" Value="" Type="Status" Byte="3" Bit="5"><Desc>FM fiscalized</Desc></Res><Res Name="FM_produced" Value="" Type="Status" Byte="3" Bit="6"><Desc>FM produced</Desc></Res><Res Name="Printer_automatic_cutting" Value="" Type="Status" Byte="4" Bit="0"><Desc>Printer: automatic cutting</Desc></Res><Res Name="External_display_transparent_display" Value="" Type="Status" Byte="4" Bit="1"><Desc>External display: transparent display</Desc></Res><Res Name="Missing_display" Value="" Type="Status" Byte="4" Bit="3"><Desc>Missing display</Desc></Res><Res Name="Drawer_automatic_opening" Value="" Type="Status" Byte="4" Bit="4"><Desc>Drawer: automatic opening</Desc></Res><Res Name="Customer_logo_included_in_the_receipt" Value="" Type="Status" Byte="4" Bit="5"><Desc>Customer logo included in the receipt</Desc></Res><Res Name="Blocking_after_10_days_without_communication" Value="" Type="Status" Byte="4" Bit="6"><Desc>Blocking after 10 days without communication</Desc></Res><Res Name="Wrong_SIM_card" Value="" Type="Status" Byte="5" Bit="0"><Desc>Wrong SIM card</Desc></Res><Res Name="Wrong_SD_card" Value="" Type="Status" Byte="5" Bit="5"><Desc>Wrong SD card</Desc></Res><Res Name="No_SIM_card" Value="" Type="Status" Byte="6" Bit="0"><Desc>No SIM card</Desc></Res><Res Name="No_GPRS_Modem" Value="" Type="Status" Byte="6" Bit="1"><Desc>No GPRS Modem</Desc></Res><Res Name="No_mobile_operator" Value="" Type="Status" Byte="6" Bit="2"><Desc>No mobile operator</Desc></Res><Res Name="No_GPRS_service" Value="" Type="Status" Byte="6" Bit="3"><Desc>No GPRS service</Desc></Res><Res Name="Near_end_of_paper" Value="" Type="Status" Byte="6" Bit="4"><Desc>Near end of paper</Desc></Res><ResFormatRaw><![CDATA[<StatusBytes[7]>]]></ResFormatRaw></Response></Command><Command Name="ReadTotalFiscalSums" CmdByte="0x6E"><FPOperation>Provides information about the total fiscal accumulative sums from sales and Storno</FPOperation><Args><Arg Name="" Value="7" Type="OptionHardcoded" MaxLen="1" /><ArgsFormatRaw><![CDATA[ <\'7\'> ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="" Value="7" Type="OptionHardcoded" MaxLen="1" /><Res Name="SumSalesTurnover" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total grand sum of sales turnover from fiscal registration</Desc></Res><Res Name="SumStornoTurnover" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total sum of Storno turnover from fiscal registration</Desc></Res><Res Name="SumSalesVAT" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total VAT sum of sales from fiscal registration</Desc></Res><Res Name="SumStornoVAT" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total VAT sum of Storno from fiscal registration</Desc></Res><Res Name="SumMacSalesTurnover" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total grand sum of maced. sales turnover from fiscal registration</Desc></Res><Res Name="SumMacStornoTurnover" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total sum of maced.Storno turnover from fiscal registration</Desc></Res><Res Name="SumMacSalesVAT" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total VAT sum of maced.sales from fiscal registration</Desc></Res><Res Name="SumMacStornoVAT" Value="" Type="Text" MaxLen="14"><Desc>14 s. for total VAT sum of maced.Storno from fiscal registration</Desc></Res><ResFormatRaw><![CDATA[<\'7\'> <;> <SumSalesTurnover[14]> <;> <SumStornoTurnover[14]> <;> <SumSalesVAT[14]> <;> <SumStornoVAT[14]> <;> <SumMacSalesTurnover[14]> <;> <SumMacStornoTurnover[14]> <;> <SumMacSalesVAT[14]> <;> <SumMacStornoVAT[14]>]]></ResFormatRaw></Response></Command><Command Name="ReadVATrates" CmdByte="0x62"><FPOperation>Provides information about the current VAT rates which are the last values stored into the FM.</FPOperation><Response ACK="false"><Res Name="VATrate0" Value="" Type="Decimal_with_format" MaxLen="7" Format="00.00%"><Desc>Value of VAT rate А from 7 symbols in format ##.##%</Desc></Res><Res Name="VATrate1" Value="" Type="Decimal_with_format" MaxLen="7" Format="00.00%"><Desc>Value of VAT rate Б from 7 symbols in format ##.##%</Desc></Res><Res Name="VATrate2" Value="" Type="Decimal_with_format" MaxLen="7" Format="00.00%"><Desc>Value of VAT rate В from 7 symbols in format ##.##%</Desc></Res><Res Name="VATrate3" Value="" Type="Decimal_with_format" MaxLen="7" Format="00.00%"><Desc>Value of VAT rate Г from 7 symbols in format ##.##%</Desc></Res><ResFormatRaw><![CDATA[<VATrate0[7]> <;> <VATrate1[7]> <;> <VATrate2[7]> <;> <VATrate3[7]>]]></ResFormatRaw></Response></Command><Command Name="ReadVersion" CmdByte="0x21"><FPOperation>Provides information about the device type, model name and version.</FPOperation><Response ACK="false"><Res Name="OptionDeviceType" Value="" Type="Option" MaxLen="1"><Options><Option Name="ECR" Value="1" /><Option Name="FPr" Value="2" /></Options><Desc>1 symbol for type of fiscal device: - \'1\'- ECR - \'2\'- FPr</Desc></Res><Res Name="Model" Value="" Type="Text" MaxLen="50"><Desc>Up to 50 symbols for Model name</Desc></Res><Res Name="Version" Value="" Type="Text" MaxLen="20"><Desc>Up to 20 symbols for Version name and Check sum</Desc></Res><ResFormatRaw><![CDATA[<DeviceType[1]> <;> <Model[50]> <;> <Version[20]>]]></ResFormatRaw></Response></Command><Command Name="ReceivedOnAccount_PaidOut" CmdByte="0x3B"><FPOperation>Registers cash received on account or paid out.</FPOperation><Args><Arg Name="OperNum" Value="" Type="Decimal" MaxLen="2"><Desc>Symbols from 1 to 20 corresponding to the operator\'s number</Desc></Arg><Arg Name="OperPass" Value="" Type="Text" MaxLen="4"><Desc>4 symbols for operator\'s password</Desc></Arg><Arg Name="reserved" Value="0" Type="OptionHardcoded" MaxLen="1" /><Arg Name="Amount" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for the amount lodged/withdrawn</Desc></Arg><Arg Name="Text" Value="" Type="Text" MaxLen="64"><Desc>TextLength-2 symbols. In the beginning and in the end of line symbol \'#\' is printed.</Desc><Meta MinLen="64" Compulsory="false" ValIndicatingPresence=";" /></Arg><ArgsFormatRaw><![CDATA[<OperNum[1..2]> <;> <OperPass[4]> <;> <reserved[\'0\']> <;> <Amount[1..10]> {<;> <Text[TextLength-2]>} ]]></ArgsFormatRaw></Args></Command><Command Name="SelectExternalDisplay" CmdByte="0x56"><FPOperation>Select type of display</FPOperation><Args><Arg Name="Option" Value="E" Type="OptionHardcoded" MaxLen="1" /><Arg Name="OptionExternalDisplay" Value="" Type="Option" MaxLen="1"><Options><Option Name="Others" Value="0" /></Options><Desc>-\'1\' -Tremol display -\'0\' - Others</Desc></Arg><ArgsFormatRaw><![CDATA[ <Option[\'E\']> <;> <ExternalDisplay[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="SellPLUfromDep" CmdByte="0x34"><FPOperation>Register the sell of department. Correction is forbidden!</FPOperation><Args><Arg Name="NamePLU" Value="" Type="Text" MaxLen="36"><Desc>36 symbols for name of sale. 34 symbols are printed on paper.</Desc></Arg><Arg Name="DepNum" Value="" Type="Decimal_plus_80h" MaxLen="2"><Desc>1 symbol for article department attachment, formed in the following manner: DepNum[HEX] + 80h example: Dep01 = 81h, Dep02 = 82h … Dep19 = 93h</Desc></Arg><Arg Name="Price" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for article\'s price.</Desc></Arg><Arg Name="OptionGoodsType" Value="" Type="Option" MaxLen="1"><Options><Option Name="importation" Value="0" /><Option Name="macedonian goods" Value="1" /></Options><Desc>1 symbol with value:  - \'1\' - macedonian goods  - \'0\' - importation</Desc></Arg><Arg Name="Quantity" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for article\'s quantity sold</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="*" /></Arg><Arg Name="DiscAddP" Value="" Type="Decimal" MaxLen="7"><Desc>Up to 7 for percentage of discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="," /></Arg><Arg Name="DiscAddV" Value="" Type="Decimal" MaxLen="8"><Desc>Up to 8 symbols for percentage of discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence=":" /></Arg><ArgsFormatRaw><![CDATA[ <NamePLU[36]> <;> <DepNum[1..2]> <;> <Price[1..10]> <;> <GoodsType[1]> {<\'*\'> <Quantity[1..10]>} {<\',\'> <DiscAddP[1..7]>} {<\':\'> <DiscAddV[1..8]>} ]]></ArgsFormatRaw></Args></Command><Command Name="SellPLUFromFD_DB" CmdByte="0x32"><FPOperation>Register the sell with specified quantity of article from the internal FD database. Correction is forbidden!</FPOperation><Args><Arg Name="OptionSign" Value="" Type="Option" MaxLen="1"><Options><Option Name="Sale" Value="+" /></Options><Desc>1 symbol with optional value:  - \'+\' -Sale</Desc><Meta MinLen="1" Compulsory="true" NoSemiColumnSeparatorAfterIt="true" /></Arg><Arg Name="PLUNum" Value="" Type="Decimal_with_format" MaxLen="5" Format="00000"><Desc>5 symbols for PLU number of FD\'s database in format #####</Desc></Arg><Arg Name="Price" Value="" Type="Decimal" MaxLen="8"><Desc>Up to 10 symbols for sale price</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="$" /></Arg><Arg Name="Quantity" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for article\'s quantity sold</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="*" /></Arg><Arg Name="DiscAddP" Value="" Type="Decimal" MaxLen="7"><Desc>Up to 7 for percentage of discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="," /></Arg><Arg Name="DiscAddV" Value="" Type="Decimal" MaxLen="8"><Desc>Up to 8 symbolsfor percentage of discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence=":" /></Arg><ArgsFormatRaw><![CDATA[ <OptionSign[1]> <PLUNum[5]> {<\'$\'> <Price[1..8]>} {<\'*\'> <Quantity[1..10]>} {<\',\'> <DiscAddP[1..7]>} {<\':\'> <DiscAddV[1..8]>} ]]></ArgsFormatRaw></Args></Command><Command Name="SellPLUwithSpecifiedVAT" CmdByte="0x31"><FPOperation>Register the sell of article with specified name, price, quantity, VAT class and/or discount/addition on the transaction. Correction is forbidden!</FPOperation><Args><Arg Name="NamePLU" Value="test" Type="Text" MaxLen="36"><Desc>36 symbols for article\'s name</Desc></Arg><Arg Name="OptionVATClass" Value="Г" Type="Option" MaxLen="1"><Options><Option Name="VAT Class 0" Value="А" /><Option Name="VAT Class 1" Value="Б" /><Option Name="VAT Class 2" Value="В" /><Option Name="VAT Class 3" Value="Г" /></Options><Desc>1 character for VAT class:  - \'А\' - VAT Class 0  - \'Б\' - VAT Class 1  - \'В\' - VAT Class 2  - \'Г\' - VAT Class 3</Desc></Arg><Arg Name="Price" Value="1" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for article\'s price.</Desc></Arg><Arg Name="OptionGoodsType" Value="1" Type="Option" MaxLen="1"><Options><Option Name="importation" Value="0" /><Option Name="macedonian goods" Value="1" /></Options><Desc>1 symbol with value:  - \'1\' - macedonian goods  - \'0\' - importation</Desc></Arg><Arg Name="Quantity" Value="1" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for quantity</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="*" /></Arg><Arg Name="DiscAddP" Value="" Type="Decimal" MaxLen="7"><Desc>Up to 7 symbols for percentage of discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="," /></Arg><Arg Name="DiscAddV" Value="" Type="Decimal" MaxLen="8"><Desc>Up to 8 symbols for value of discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence=":" /></Arg><ArgsFormatRaw><![CDATA[ <NamePLU[36]> <;> <OptionVATClass[1]> <;> <Price[1..10]><;> <GoodsType[1]> {<\'*\'> <Quantity[1..10]>} {<\',\'> <DiscAddP[1..7]>} {<\':\'> <DiscAddV[1..8]>} ]]></ArgsFormatRaw></Args></Command><Command Name="SetActiveLogo" CmdByte="0x23"><FPOperation>Stores in the memory the graphic file under stated number. Prints information about loaded in the printer graphic files.</FPOperation><Args><Arg Name="LogoNumber" Value="" Type="Text" MaxLen="1"><Desc>1 character value from \'0\' to \'9\' or \'?\'. The number sets the active logo number, and the \'?\' invokes only printing of information</Desc></Arg><ArgsFormatRaw><![CDATA[ <LogoNumber[1]> ]]></ArgsFormatRaw></Args></Command><Command Name="SetDateTime" CmdByte="0x48"><FPOperation>Sets the date and time and prints out the current values.</FPOperation><Args><Arg Name="DateTime" Value="" Type="DateTime" MaxLen="10" Format="dd-MM-yy HH:mm:ss"><Desc>Date Time parameter in format: DD-MM-YY HH:MM:SS</Desc></Arg><ArgsFormatRaw><![CDATA[ <DateTime "DD-MM-YY HH:MM:SS"> ]]></ArgsFormatRaw></Args></Command><Command Name="SetIDandVATnum" CmdByte="0x41"><FPOperation>Stores the VAT and ID numbers into the operative memory.</FPOperation><Args><Arg Name="Password" Value="" Type="Text" MaxLen="6"><Desc>6 symbols string</Desc></Arg><Arg Name="" Value="1" Type="OptionHardcoded" MaxLen="1" /><Arg Name="IDNum" Value="" Type="Text" MaxLen="13"><Desc>13 symbols owner\'s ID number</Desc></Arg><Arg Name="VATNum" Value="" Type="Text" MaxLen="15"><Desc>15 symbols for owner\'s VAT number</Desc></Arg><ArgsFormatRaw><![CDATA[ <Password[6]> <;> <\'1\'> <;> <IDNum[13]> <;> <VATNum[15]> ]]></ArgsFormatRaw></Args></Command><Command Name="Subtotal" CmdByte="0x33"><FPOperation>Calculate the subtotal amount with printing and display visualization options. Provide information about values of the calculated amounts. If a percent or value discount/addition has been specified the subtotal and the discount/addition value will be printed regardless the parameter for printing.</FPOperation><Args><Arg Name="OptionPrinting" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol with value:  - \'1\' - Yes  - \'0\' - No</Desc></Arg><Arg Name="OptionDisplay" Value="" Type="Option" MaxLen="1"><Options><Option Name="No" Value="0" /><Option Name="Yes" Value="1" /></Options><Desc>1 symbol with value:  - \'1\' - Yes  - \'0\' - No</Desc></Arg><Arg Name="DiscAddV" Value="" Type="Decimal" MaxLen="8"><Desc>Up to 8 symbols for the value of the discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence=":" /></Arg><Arg Name="DiscAddP" Value="" Type="Decimal" MaxLen="7"><Desc>Up to 7 symbols for the percentage value of the discount/addition. Use minus sign \'-\' for discount</Desc><Meta MinLen="1" Compulsory="false" ValIndicatingPresence="," /></Arg><ArgsFormatRaw><![CDATA[ <OptionPrinting[1]> <;> <OptionDisplay[1]> {<\':\'> <DiscAddV[1..8]>} {<\',\'> <DiscAddP[1..7]>} ]]></ArgsFormatRaw></Args><Response ACK="false"><Res Name="SubtotalValue" Value="" Type="Decimal" MaxLen="10"><Desc>Up to 10 symbols for the value of the subtotal amount</Desc></Res><ResFormatRaw><![CDATA[<SubtotalValue[1..10]>]]></ResFormatRaw></Response></Command></Defs>';
	return this.ServerSendDefs(defs);
}

Tremol.Enums = Tremol.Enums || {
	/**
	 * @typedef {Tremol.Enums.OptionServiceMode} Tremol.Enums.OptionServiceMode
	 * @readonly
	 * @enum
	 */
	OptionServiceMode: {
		Sales_mode: '0',
		Service_mode: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionActivationRS} Tremol.Enums.OptionActivationRS
	 * @readonly
	 * @enum
	 */
	OptionActivationRS: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionReceiptType} Tremol.Enums.OptionReceiptType
	 * @readonly
	 * @enum
	 */
	OptionReceiptType: {
		Sale: '1',
		Storno: '0'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionPrintType} Tremol.Enums.OptionPrintType
	 * @readonly
	 * @enum
	 */
	OptionPrintType: {
		Postponed_printing: '2',
		Step_by_step_printing: '0'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionPaymentType} Tremol.Enums.OptionPaymentType
	 * @readonly
	 * @enum
	 */
	OptionPaymentType: {
		Card: '1',
		Cash: '0',
		Credit: '3',
		Currency: '4',
		Voucher: '2'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionChange} Tremol.Enums.OptionChange
	 * @readonly
	 * @enum
	 */
	OptionChange: {
		With_Change: '0',
		Without_Change: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionChangeType} Tremol.Enums.OptionChangeType
	 * @readonly
	 * @enum
	 */
	OptionChangeType: {
		Change_In_Cash: '0',
		Change_In_Currency: '2',
		Same_As_The_payment: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionZeroing} Tremol.Enums.OptionZeroing
	 * @readonly
	 * @enum
	 */
	OptionZeroing: {
		Without_zeroing: 'X',
		Zeroing: 'Z'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionCodeType} Tremol.Enums.OptionCodeType
	 * @readonly
	 * @enum
	 */
	OptionCodeType: {
		CODABAR: '6',
		CODE_128: 'I',
		CODE_39: '4',
		CODE_93: 'H',
		EAN_13: '2',
		EAN_8: '3',
		ITF: '5',
		UPC_A: '0',
		UPC_E: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionDecimalPointPosition} Tremol.Enums.OptionDecimalPointPosition
	 * @readonly
	 * @enum
	 */
	OptionDecimalPointPosition: {
		Fractions: '2',
		Whole_numbers: '0'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionVATClass} Tremol.Enums.OptionVATClass
	 * @readonly
	 * @enum
	 */
	OptionVATClass: {
		VAT_Class_0: 'А',
		VAT_Class_1: 'Б',
		VAT_Class_2: 'В',
		VAT_Class_3: 'Г'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionFooterLine} Tremol.Enums.OptionFooterLine
	 * @readonly
	 * @enum
	 */
	OptionFooterLine: {
		Footer_1: 'F1',
		Footer_2: 'F2',
		Footer_3: 'F3'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionHeaderLine} Tremol.Enums.OptionHeaderLine
	 * @readonly
	 * @enum
	 */
	OptionHeaderLine: {
		Header_1: '1',
		Header_2: '2',
		Header_3: '3',
		Header_4: '4',
		Header_5: '5',
		Header_6: '6',
		ID_number: '7',
		VAT_number: '8'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionPrintLogo} Tremol.Enums.OptionPrintLogo
	 * @readonly
	 * @enum
	 */
	OptionPrintLogo: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionAutoOpenDrawer} Tremol.Enums.OptionAutoOpenDrawer
	 * @readonly
	 * @enum
	 */
	OptionAutoOpenDrawer: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionAutoCut} Tremol.Enums.OptionAutoCut
	 * @readonly
	 * @enum
	 */
	OptionAutoCut: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionExternalDispManagement} Tremol.Enums.OptionExternalDispManagement
	 * @readonly
	 * @enum
	 */
	OptionExternalDispManagement: {
		Auto: '0',
		Manual: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionArticleReportType} Tremol.Enums.OptionArticleReportType
	 * @readonly
	 * @enum
	 */
	OptionArticleReportType: {
		Brief: '0',
		Detailed: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionEnableCurrency} Tremol.Enums.OptionEnableCurrency
	 * @readonly
	 * @enum
	 */
	OptionEnableCurrency: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionWorkOperatorCount} Tremol.Enums.OptionWorkOperatorCount
	 * @readonly
	 * @enum
	 */
	OptionWorkOperatorCount: {
		More: '0',
		One: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionPaymentNum} Tremol.Enums.OptionPaymentNum
	 * @readonly
	 * @enum
	 */
	OptionPaymentNum: {
		Payment_1: '1',
		Payment_2: '2',
		Payment_3: '3',
		Payment_4: '4'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionPrice} Tremol.Enums.OptionPrice
	 * @readonly
	 * @enum
	 */
	OptionPrice: {
		Free_price_is_disable_valid_only_programmed_price: '0',
		Free_price_is_enable: '1',
		Limited_price: '2'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionQuantityType} Tremol.Enums.OptionQuantityType
	 * @readonly
	 * @enum
	 */
	OptionQuantityType: {
		Availability_of_PLU_stock_is_not_monitored: '0',
		Disable_negative_quantity: '1',
		Enable_negative_quantity: '2'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionIsReceiptOpened} Tremol.Enums.OptionIsReceiptOpened
	 * @readonly
	 * @enum
	 */
	OptionIsReceiptOpened: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionInitiatedPayment} Tremol.Enums.OptionInitiatedPayment
	 * @readonly
	 * @enum
	 */
	OptionInitiatedPayment: {
		initiated_payment: '1',
		not_initiated_payment: '0'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionFinalizedPayment} Tremol.Enums.OptionFinalizedPayment
	 * @readonly
	 * @enum
	 */
	OptionFinalizedPayment: {
		finalized_payment: '1',
		not_finalized_payment: '0'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionPowerDownInReceipt} Tremol.Enums.OptionPowerDownInReceipt
	 * @readonly
	 * @enum
	 */
	OptionPowerDownInReceipt: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionExternalType} Tremol.Enums.OptionExternalType
	 * @readonly
	 * @enum
	 */
	OptionExternalType: {
		Others: '0',
		Tremol_display: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionRecieptSend} Tremol.Enums.OptionRecieptSend
	 * @readonly
	 * @enum
	 */
	OptionRecieptSend: {
		automatic_sending: '1',
		without_sending: '0'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionDeviceType} Tremol.Enums.OptionDeviceType
	 * @readonly
	 * @enum
	 */
	OptionDeviceType: {
		ECR: '1',
		FPr: '2'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionExternalDisplay} Tremol.Enums.OptionExternalDisplay
	 * @readonly
	 * @enum
	 */
	OptionExternalDisplay: {
		Others: '0'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionGoodsType} Tremol.Enums.OptionGoodsType
	 * @readonly
	 * @enum
	 */
	OptionGoodsType: {
		importation: '0',
		macedonian_goods: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionSign} Tremol.Enums.OptionSign
	 * @readonly
	 * @enum
	 */
	OptionSign: {
		Sale: '+'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionPrinting} Tremol.Enums.OptionPrinting
	 * @readonly
	 * @enum
	 */
	OptionPrinting: {
		No: '0',
		Yes: '1'
	},
	
	/**
	 * @typedef {Tremol.Enums.OptionDisplay} Tremol.Enums.OptionDisplay
	 * @readonly
	 * @enum
	 */
	OptionDisplay: {
		No: '0',
		Yes: '1'
	}
};