from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

NILVERA_ERROR_CODE_MESSAGES = {
    # 404 errors
    3000: _lt("Tag for the Recipient Not Found"),
    3001: _lt("Tag for the Sender Not Found"),
    3017: _lt("You do not have a package with this code"),
    3030: _lt("API Not Found"),

    # 409 errors
    1000: _lt("The sent Tax Identification Number (TIN) does not match the company"),
    1001: _lt("Nilvera UUID (ETTN) is already registered in the system"),
    1004: _lt("This e-invoice has been previously added"),
    1005: _lt("The e-invoice series has been used before"),
    1015: _lt("The record has been added before"),

    # 422 errors
    2000: _lt("You do not have sufficient credits"),
    2004: _lt("Record generation unsuccessful"),
    2015: _lt("Schema/Schematron error"),
    2024: _lt("The document scenario must be e-Archive"),
    2025: _lt("The recipient is an e-invoice taxpayer. The e-Archive invoice cannot be sent"),
    2051: _lt("The Sender is not an e-Invoice Payer"),
    2052: _lt("Buyer's Alias is Not in Use"),
    2053: _lt("The Buyer Became an e-Invoice Taxpayer"),
    2054: _lt("The Buyer is Not an E-Invoice Payer"),
    2057: _lt("An Error Occurred While Fetching E-Invoice Labels"),
    2059: _lt("E-Invoice Scenario Must Be Public"),
    2060: _lt("Invoice Scenario Must Be e-Archive Invoice"),
    2061: _lt("e-Invoice Scenario Should Not Be Public"),
    2063: _lt("Since the Invoice Scenario is an e-Archive Invoice, it cannot be sent to the e-Invoice sender"),
    2065: _lt("e-Invoice Serial Field Cannot Be Blank"),
    2075: _lt("Your Credit Package Has Expired"),
    2078: _lt("Your Credit Package Does Not Have Enough Credit"),
    2100: _lt("Series and Document Year Mismatch"),
}
