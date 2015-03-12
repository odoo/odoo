
# JEM : Yes, their error mapping is different for each operation !


_DOCSAWAY_ERROR_ACCOUNT = {
    '-1'  : 'Submitted JSON object is malformed.',
    '001' : 'Submitting an empty value for a mandatory field.',
    '002' : 'User authentication information is incorrect.',
    '003' : 'User account has been deactivated.',
    '004' : 'API connection has not been found.',
    '005' : 'Audit reference value not recognized.',
    '006' : 'Audit action value not recognized.',
    '007' : 'Audit reference specified is not accessible via your account.',
    '008' : 'Submitted a string length larger than allowed.',
}

_DOCSAWAY_ERROR_STATION = {
    '-1'  : 'Submitted JSON object is malformed.',
    '-2'  : 'Action property not recognized.',
    '001' : 'Submitted an empty value for a mandatory field.',
    '002' : 'User authentication information is incorrect.',
    '003' : 'User account has been deactivated.',
    '004' : 'API connection has not been found.',
    '005' : 'File containing the data was not found, check property values being submitted are correct.',
    '006' : 'Submitted a string length larger than allowed.',
    '007' : 'A value specified within a set method was not recognized.',
    '008' : 'Country code not recognized.',
}

_DOCSAWAY_ERROR_PRICE = {
    '-1'  : 'Submitted JSON object is malformed.',
    '001' : 'Submitted an empty value for a mandatory field.',
    '002' : 'User authentication information is incorrect.',
    '003' : 'User account has been deactivated.',
    '004' : 'API connection has not been found.',
    '005' : 'A mandatory set method has not been set.',
    '006' : 'Unable to calculate price.',
    '007' : 'Submitted a string length larger than allowed.',
    '008' : 'A value specified within a property was not recognized.',
    '009' : 'PDF document page count exceeded maximum allowed pages.'
}

_DOCSAWAY_ERROR_MAIL = {
    '-1'  : 'Submitted JSON object is malformed.',
    '001' : 'Submitting an empty value for a mandatory field.',
    '002' : 'User authentication information is incorrect.',
    '003' : 'User account has been deactivated.',
    '004' : 'Entered character set has not been recognized.',
    '005' : 'Character set was not specified.',
    '006' : 'Set methods declared in incorrect order.',
    '007' : 'Character set used for SET methods has failed to convert to system character set.',
    '008' : 'Submitted a string length larger than allowed.',
    '009' : 'Country code not recognized.',
    '010' : 'API mode not recognized.',
    '011' : 'File method empty, PDF not set.',
    '012' : 'PDF password does not match the account password.',
    '013' : 'API class failed to open uploaded PDF.',
    '014' : 'API class failed to save uploaded PDF.',
    '015' : 'The uploaded PDF document was empty.',
    '016' : 'PDF document not located by the API class.',
    '017' : 'Document uploaded was not a PDF.',
    '018' : 'API page count class failed.',
    '019' : 'PDF document exceeded maximum allowed pages.',
    '020' : 'A value specified within the PrintingStation properties was not recognized.',
    '021' : 'Specified printing station was not found.',
    '022' : 'Specified courier is not available.',
    '023' : 'Specified ink setting for a selected station is not available.',
    '024' : 'Specified printing station does not support the recipients country.',
    '025' : 'Specified printing station was not recognized.',
    '026' : 'Mandatory properties needed to locate the printing station are incorrect.',
    '027' : 'An internal script error has occurred and was captured.',
    '028' : 'An internal script error occurred while accessing the coversheet class.',
    '029' : 'An internal script error occurred while accessing the pricing class.',
    '030' : 'An internal script error occurred while accessing the database.',
    '031' : 'An internal script error occurred while merging coversheet and PDF document.',
    '032' : 'Your account has insufficient funds for your document transaction.',
    '033' : 'An internal error occurred while changing the status of your transaction.',
    '034' : 'Your selected station can not be used as you have selected the stations country as blocked in your account.',
    '035' : 'Your PDF document exceeds the maximum file size allowed, currently set at 2Mb.',
    '036' : 'The server is extremely busy to the point access for account update could not be given.',
    '037' : 'The REST API uses internal sessions while processing a transaction, a problem occurred when generating a session.',
    '038' : 'Specified courier was not found.',
    '039' : 'Specified paper setting for a selected station is not available.',
    '040' : 'API connection has not been found.'
}

