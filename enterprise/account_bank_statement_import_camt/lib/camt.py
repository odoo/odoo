
import math
import re
from functools import partial

from odoo.exceptions import ValidationError
from odoo.tools import float_compare

# keep code as-is but do not translate,
# the language is not known in this context
_lt = lambda x: x  # noqa: E731


# Codes from the updated document of 30 june 2017
# pylint: disable=duplicate-key
codes = {
    # ExternalBankTransactionDomain1Code #######################################
    'PMNT': _lt('Payments'),
    'CAMT': _lt('Cash Management'),
    'DERV': _lt('Derivatives'),
    'LDAS': _lt('Loans, Deposits & Syndications'),
    'FORX': _lt('Foreign Exchange'),
    'PMET': _lt('Precious Metal'),
    'CMDT': _lt('Commodities'),
    'TRAD': _lt('Trade Services'),
    'SECU': _lt('Securities'),
    'ACMT': _lt('Account Management'),
    'XTND': _lt('Extended Domain'),
    # ExternalBankTransactionFamily1Code #######################################
    'RCDT': _lt('Received Credit Transfers'),  # Payments
    'ICDT': _lt('Issued Credit Transfers'),
    'RCCN': _lt('Received Cash Concentration Transactions'),
    'ICCN': _lt('Issued Cash Concentration Transactions'),
    'RDDT': _lt('Received Direct Debits'),
    'IDDT': _lt('Issued Direct Debits'),
    'RCHQ': _lt('Received Cheques'),
    'ICHQ': _lt('Issued Cheques'),
    'CCRD': _lt('Customer Card Transactions'),
    'MCRD': _lt('Merchant Card Transactions'),
    'LBOX': _lt('Lockbox Transactions'),
    'CNTR': _lt('Counter Transactions'),
    'DRFT': _lt('Drafts/BillOfOrders'),
    'RRCT': _lt('Received Real Time Credit Transfer'),
    'IRCT': _lt('Issued Real Time Credit Transfer'),
    'CAPL': _lt('Cash Pooling'),  # Cash Management
    'ACCB': _lt('Account Balancing'),
    'OCRD': _lt('OTC Derivatives – Credit Derivatives'),  # Derivatives
    'OIRT': _lt('OTC Derivatives – Interest Rates'),
    'OEQT': _lt('OTC Derivatives – Equity'),
    'OBND': _lt('OTC Derivatives – Bonds'),
    'OSED': _lt('OTC Derivatives – Structured Exotic Derivatives'),
    'OSWP': _lt('OTC Derivatives – Swaps'),
    'LFUT': _lt('Listed Derivatives – Futures'),
    'LOPT': _lt('Listed Derivatives – Options'),
    'FTLN': _lt('Fixed Term Loans'),  # Loans, Deposits & Syndications
    'NTLN': _lt('Notice Loans'),
    'FTDP': _lt('Fixed Term Deposits'),
    'NTDP': _lt('Notice Deposits'),
    'MGLN': _lt('Mortgage Loans'),
    'CSLN': _lt('Consumer Loans'),
    'SYDN': _lt('Syndications'),
    'SPOT': _lt('Spots'),  # Foreign Exchange
    'FWRD': _lt('Forwards'),
    'SWAP': _lt('Swaps'),
    'FTUR': _lt('Futures'),
    'NDFX': _lt('Non Deliverable'),
    'SPOT': _lt('Spots'),  # Precious Metal
    'FTUR': _lt('Futures'),
    'OPTN': _lt('Options'),
    'DLVR': _lt('Delivery'),
    'SPOT': _lt('Spots'),  # Commodities
    'FTUR': _lt('Futures'),
    'OPTN': _lt('Options'),
    'DLVR': _lt('Delivery'),
    'LOCT': _lt('Stand-By Letter Of Credit'),  # Trade Services
    'DCCT': _lt('Documentary Credit'),
    'CLNC': _lt('Clean Collection'),
    'DOCC': _lt('Documentary Collection'),
    'GUAR': _lt('Guarantees'),
    'SETT': _lt('Trade, Clearing and Settlement'),  # Securities
    'NSET': _lt('Non Settled'),
    'BLOC': _lt('Blocked Transactions'),
    'OTHB': _lt('CSD Blocked Transactions'),
    'COLL': _lt('Collateral Management'),
    'CORP': _lt('Corporate Action'),
    'CUST': _lt('Custody'),
    'COLC': _lt('Custody Collection'),
    'LACK': _lt('Lack'),
    'CASH': _lt('Miscellaneous Securities Operations'),
    'OPCL': _lt('Opening & Closing'),  # Account Management
    'ACOP': _lt('Additional Miscellaneous Credit Operations'),
    'ADOP': _lt('Additional Miscellaneous Debit Operations'),
    # ExternalBankTransactionSubFamily1Code ####################################
    # Generic Sub-Families
    'FEES': _lt('Fees'),  # Miscellaneous Credit Operations
    'COMM': _lt('Commission'),
    'COME': _lt('Commission excluding taxes'),
    'COMI': _lt('Commission including taxes'),
    'COMT': _lt('Non Taxable commissions'),
    'TAXE': _lt('Taxes'),
    'CHRG': _lt('Charges'),
    'INTR': _lt('Interest'),
    'RIMB': _lt('Reimbursements'),
    'ADJT': _lt('Adjustments'),
    'FEES': _lt('Fees'),  # Miscellaneous Debit Operations
    'COMM': _lt('Commission'),
    'COME': _lt('Commission excluding taxes'),
    'COMI': _lt('Commission including taxes'),
    'COMT': _lt('Non Taxable commissions'),
    'TAXE': _lt('Taxes'),
    'CHRG': _lt('Charges'),
    'INTR': _lt('Interest'),
    'RIMB': _lt('Reimbursements'),
    'ADJT': _lt('Adjustments'),
    'IADD': _lt('Invoice Accepted with Differed Due Date'),
    'FEES': _lt('Fees'),  # Generic Sub-Families
    'COMM': _lt('Commission'),
    'COME': _lt('Commission excluding taxes'),
    'COMI': _lt('Commission including taxes'),
    'COMT': _lt('Non Taxable commissions'),
    'TAXE': _lt('Taxes'),
    'CHRG': _lt('Charges'),
    'INTR': _lt('Interest'),
    'RIMB': _lt('Reimbursements'),
    'DAJT': _lt('Credit Adjustments'),
    'CAJT': _lt('Debit Adjustments'),
    # Payments Sub-Families
    'BOOK': _lt('Internal Book Transfer'),  # Received Credit Transfer
    'STDO': _lt('Standing Order'),
    'XBST': _lt('Cross-Border Standing Order'),
    'ESCT': _lt('SEPA Credit Transfer'),
    'DMCT': _lt('Domestic Credit Transfer'),
    'XBCT': _lt('Cross-Border Credit Transfer'),
    'VCOM': _lt('Credit Transfer with agreed Commercial Information'),
    'FICT': _lt('Financial Institution Credit Transfer'),
    'PRCT': _lt('Priority Credit Transfer'),
    'SALA': _lt('Payroll/Salary Payment'),
    'XBSA': _lt('Cross-Border Payroll/Salary Payment'),
    'SDVA': _lt('Same Day Value Credit Transfer'),
    'RPCR': _lt('Reversal due to Payment Cancellation Request'),
    'RRTN': _lt('Reversal due to Payment Return/reimbursement of a Credit Transfer'),
    'AUTT': _lt('Automatic Transfer'),
    'ATXN': _lt('ACH Transaction'),
    'ACOR': _lt('ACH Corporate Trade'),
    'APAC': _lt('ACH Pre-Authorised'),
    'ASET': _lt('ACH Settlement'),
    'ARET': _lt('ACH Return'),
    'AREV': _lt('ACH Reversal'),
    'ACDT': _lt('ACH Credit'),
    'ADBT': _lt('ACH Debit'),
    'TTLS': _lt('Treasury Tax And Loan Service'),
    'BOOK': _lt('Internal Book Transfer'),  # Issued Credit Transfer
    'STDO': _lt('Standing Order'),
    'XBST': _lt('Cross-Border Standing Order'),
    'ESCT': _lt('SEPA Credit Transfer'),
    'DMCT': _lt('Domestic Credit Transfer'),
    'XBCT': _lt('Cross-Border Credit Transfer'),
    'FICT': _lt('Financial Institution Credit Transfer'),
    'PRCT': _lt('Priority Credit Transfer'),
    'VCOM': _lt('Credit Transfer with agreed Commercial Information'),
    'SALA': _lt('Payroll/Salary Payment'),
    'XBSA': _lt('Cross-Border Payroll/Salary Payment'),
    'RPCR': _lt('Reversal due to Payment Cancellation Request'),
    'RRTN': _lt('Reversal due to Payment Return/reimbursement of a Credit Transfer'),
    'SDVA': _lt('Same Day Value Credit Transfer'),
    'AUTT': _lt('Automatic Transfer'),
    'ATXN': _lt('ACH Transaction'),
    'ACOR': _lt('ACH Corporate Trade'),
    'APAC': _lt('ACH Pre-Authorised'),
    'ASET': _lt('ACH Settlement'),
    'ARET': _lt('ACH Return'),
    'AREV': _lt('ACH Reversal'),
    'ACDT': _lt('ACH Credit'),
    'ADBT': _lt('ACH Debit'),
    'TTLS': _lt('Treasury Tax And Loan Service'),
    'COAT': _lt('Corporate Own Account Transfer'),  # Received Cash Concentration
    'ICCT': _lt('Intra Company Transfer'),
    'XICT': _lt('Cross-Border Intra Company Transfer'),
    'FIOA': _lt('Financial Institution Own Account Transfer'),
    'BACT': _lt('Branch Account Transfer'),
    'ACON': _lt('ACH Concentration'),
    'COAT': _lt('Corporate Own Account Transfer'),  # Issued Cash Concentration
    'ICCT': _lt('Intra Company Transfer'),
    'XICT': _lt('Cross-Border Intra Company Transfer'),
    'FIOA': _lt('Financial Institution Own Account Transfer'),
    'BACT': _lt('Branch Account Transfer'),
    'ACON': _lt('ACH Concentration'),
    'PMDD': _lt('Direct Debit'),  # Received Direct Debit
    'URDD': _lt('Direct Debit under reserve'),
    'ESDD': _lt('SEPA Core Direct Debit'),
    'BBDD': _lt('SEPA B2B Direct Debit'),
    'XBDD': _lt('Cross-Border Direct Debit'),
    'OODD': _lt('One-Off Direct Debit'),
    'PADD': _lt('Pre-Authorised Direct Debit'),
    'FIDD': _lt('Financial Institution Direct Debit Payment'),
    'RCDD': _lt('Reversal due to a Payment Cancellation Request'),
    'UPDD': _lt('Reversal due to Return/Unpaid Direct Debit'),
    'PRDD': _lt('Reversal due to Payment Reversal'),
    'PMDD': _lt('Direct Debit Payment'),  # Issued Direct Debit
    'URDD': _lt('Direct Debit under reserve'),
    'ESDD': _lt('SEPA Core Direct Debit'),
    'BBDD': _lt('SEPA B2B Direct Debit'),
    'OODD': _lt('One-Off Direct Debit'),
    'XBDD': _lt('Cross-Border Direct Debit'),
    'PADD': _lt('Pre-Authorised Direct Debit'),
    'FIDD': _lt('Financial Institution Direct Debit Payment'),
    'RCDD': _lt('Reversal due to a Payment Cancellation Request'),
    'UPDD': _lt('Reversal due to Return/Unpaid Direct Debit'),
    'PRDD': _lt('Reversal due to Payment Reversal'),
    'CCHQ': _lt('Cheque'),  # Received Cheque
    'URCQ': _lt('Cheque Under Reserve'),
    'UPCQ': _lt('Unpaid Cheque'),
    'CQRV': _lt('Cheque Reversal'),
    'CCCH': _lt('Certified Customer Cheque'),
    'CLCQ': _lt('Circular Cheque'),
    'NPCC': _lt('Non-Presented Circular Cheque'),
    'CRCQ': _lt('Crossed Cheque'),
    'ORCQ': _lt('Order Cheque'),
    'OPCQ': _lt('Open Cheque'),
    'BCHQ': _lt('Bank Cheque'),
    'XBCQ': _lt('Foreign Cheque'),
    'XRCQ': _lt('Foreign Cheque Under Reserve'),
    'XPCQ': _lt('Unpaid Foreign Cheque'),
    'CDIS': _lt('Controlled Disbursement'),
    'ARPD': _lt('ARP Debit'),
    'CASH': _lt('Cash Letter'),
    'CSHA': _lt('Cash Letter Adjustment'),
    'CCHQ': _lt('Cheque'),  # Issued Cheque
    'URCQ': _lt('Cheque Under Reserve'),
    'UPCQ': _lt('Unpaid Cheque'),
    'CQRV': _lt('Cheque Reversal'),
    'CCCH': _lt('Certified Customer Cheque'),
    'CLCQ': _lt('Circular Cheque'),
    'NPCC': _lt('Non-Presented Circular Cheque'),
    'CRCQ': _lt('Crossed Cheque'),
    'ORCQ': _lt('Order Cheque'),
    'OPCQ': _lt('Open Cheque'),
    'BCHQ': _lt('Bank Cheque'),
    'XBCQ': _lt('Foreign Cheque'),
    'XRCQ': _lt('Foreign Cheque Under Reserve'),
    'XPCQ': _lt('Unpaid Foreign Cheque'),
    'CDIS': _lt('Controlled Disbursement'),
    'ARPD': _lt('ARP Debit'),
    'CASH': _lt('Cash Letter'),
    'CSHA': _lt('Cash Letter Adjustment'),
    'CWDL': _lt('Cash Withdrawal'),  # Customer Card Transaction
    'CDPT': _lt('Cash Deposit'),
    'XBCW': _lt('Cross-Border Cash Withdrawal'),
    'POSD': _lt('Point-of-Sale (POS) Payment - Debit Card'),
    'POSC': _lt('Credit Card Payment'),
    'XBCP': _lt('Cross-Border Credit Card Payment'),
    'SMRT': _lt('Smart-Card Payment'),
    'POSP': _lt('Point-of-Sale (POS) Payment'),  # Merchant Card Transaction
    'POSC': _lt('Credit Card Payment'),
    'SMCD': _lt('Smart-Card Payment'),
    'UPCT': _lt('Unpaid Card Transaction'),
    'CDPT': _lt('Cash Deposit'),  # Counter Transaction
    'CWDL': _lt('Cash Withdrawal'),
    'BCDP': _lt('Branch Deposit'),
    'BCWD': _lt('Branch Withdrawal'),
    'CHKD': _lt('Cheque Deposit'),
    'MIXD': _lt('Mixed Deposit'),
    'MSCD': _lt('Miscellaneous Deposit'),
    'FCDP': _lt('Foreign Currency Deposit'),
    'FCWD': _lt('Foreign Currency Withdrawal'),
    'TCDP': _lt('Travellers Cheques Deposit'),
    'TCWD': _lt('Travellers Cheques Withdrawal'),
    'LBCA': _lt('Credit Adjustment'),  # Lockbox
    'LBDB': _lt('Debit'),
    'LBDP': _lt('Deposit'),
    'STAM': _lt('Settlement at Maturity'),  # Drafts / Bill to Order
    'STLR': _lt('Settlement under reserve'),
    'DDFT': _lt('Discounted Draft'),
    'UDFT': _lt('Dishonoured/Unpaid Draft'),
    'DMCG': _lt('Draft Maturity Change'),
    'BOOK': _lt('Internal Book Transfer'),  # Received Real-Time Credit Transfer
    'STDO': _lt('Standing Order'),
    'XBST': _lt('Cross-Border Standing Order'),
    'ESCT': _lt('SEPA Credit Transfer'),
    'DMCT': _lt('Domestic Credit Transfer'),
    'XBCT': _lt('Cross-Border Credit Transfer'),
    'VCOM': _lt('Credit Transfer with agreed Commercial Information'),
    'FICT': _lt('Financial Institution Credit Transfer'),
    'PRCT': _lt('Priority Credit Transfer'),
    'SALA': _lt('Payroll/Salary Payment'),
    'XBSA': _lt('Cross-Border Payroll/Salary Payment'),
    'SDVA': _lt('Same Day Value Credit Transfer'),
    'RPCR': _lt('Reversal due to Payment Cancellation Request'),
    'RRTN': _lt('Reversal due to Payment Return/reimbursement of a Credit Transfer'),
    'AUTT': _lt('Automatic Transfer'),
    'ATXN': _lt('ACH Transaction'),
    'ACOR': _lt('ACH Corporate Trade'),
    'APAC': _lt('ACH Pre-Authorised'),
    'ASET': _lt('ACH Settlement'),
    'ARET': _lt('ACH Return'),
    'AREV': _lt('ACH Reversal'),
    'ACDT': _lt('ACH Credit'),
    'ADBT': _lt('ACH Debit'),
    'TTLS': _lt('Treasury Tax And Loan Service'),
    'BOOK': _lt('Internal Book Transfer'),  # Issued Real-Time Credit Transfer
    'STDO': _lt('Standing Order'),
    'XBST': _lt('Cross-Border Standing Order'),
    'ESCT': _lt('SEPA Credit Transfer'),
    'DMCT': _lt('Domestic Credit Transfer'),
    'XBCT': _lt('Cross-Border Credit Transfer'),
    'FICT': _lt('Financial Institution Credit Transfer'),
    'PRCT': _lt('Priority Credit Transfer'),
    'VCOM': _lt('Credit Transfer with agreed Commercial Information'),
    'SALA': _lt('Payroll/Salary Payment'),
    'XBSA': _lt('Cross-Border Payroll/Salary Payment'),
    'RPCR': _lt('Reversal due to Payment Cancellation Request'),
    'RRTN': _lt('Reversal due to Payment Return/reimbursement of a Credit Transfer'),
    'SDVA': _lt('Same Day Value Credit Transfer'),
    'AUTT': _lt('Automatic Transfer'),
    'ATXN': _lt('ACH Transaction'),
    'ACOR': _lt('ACH Corporate Trade'),
    'APAC': _lt('ACH Pre-Authorised'),
    'ASET': _lt('ACH Settlement'),
    'ARET': _lt('ACH Return'),
    'AREV': _lt('ACH Reversal'),
    'ACDT': _lt('ACH Credit'),
    'ADBT': _lt('ACH Debit'),
    'TTLS': _lt('Treasury Tax And Loan Service'),
    # Cash Management Sub-Families
    'XBRD': _lt('Cross-Border'),  # Cash Pooling
    'ZABA': _lt('Zero Balancing'),  # Account Balancing
    'SWEP': _lt('Sweeping'),
    'TOPG': _lt('Topping'),
    'DSBR': _lt('Controlled Disbursement'),
    'ODFT': _lt('Overdraft'),
    'XBRD': _lt('Cross-Border'),
    # Derivatives Sub-Families
    'SWUF': _lt('Upfront Payment'),
    'SWRS': _lt('Reset Payment'),
    'SWPP': _lt('Partial Payment'),
    'SWFP': _lt('Final Payment'),
    'SWCC': _lt('Client Owned Collateral'),
    # Loans, Deposits & Syndications Sub-Families
    'DDWN': _lt('Drawdown'),
    'RNEW': _lt('Renewal'),
    'PPAY': _lt('Principal Payment'),
    'DPST': _lt('Deposit'),
    'RPMT': _lt('Repayment'),
    # Trade Services Sub-Families
    'FRZF': _lt('Freeze of funds'),
    'SOSI': _lt('Settlement of Sight Import document'),
    'SOSE': _lt('Settlement of Sight Export document'),
    'SABG': _lt('Settlement against bank guarantee'),
    'STLR': _lt('Settlement under reserve'),
    'STLR': _lt('Settlement under reserve'),
    'STAC': _lt('Settlement after collection'),
    'STLM': _lt('Settlement'),
    # Securities Sub-Families
    'PAIR': _lt('Pair-Off'),  # Trade, Clearing and Settlement & Non Settled
    'TRAD': _lt('Trade'),
    'NETT': _lt('Netting'),
    'TRPO': _lt('Triparty Repo'),
    'TRVO': _lt('Triparty Reverse Repo'),
    'RVPO': _lt('Reverse Repo'),
    'REPU': _lt('Repo'),
    'SECB': _lt('Securities Borrowing'),
    'SECL': _lt('Securities Lending'),
    'BSBO': _lt('Buy Sell Back'),
    'BSBC': _lt('Sell Buy Back'),
    'FCTA': _lt('Factor Update'),
    'ISSU': _lt('Depositary Receipt Issue'),
    'INSP': _lt('Inspeci/Share Exchange'),
    'OWNE': _lt('External Account Transfer'),
    'OWNI': _lt('Internal Account Transfer'),
    'NSYN': _lt('Non Syndicated'),
    'PLAC': _lt('Placement'),
    'PORT': _lt('Portfolio Move'),
    'SYND': _lt('Syndicated'),
    'TBAC': _lt('TBA closing'),
    'TURN': _lt('Turnaround'),
    'REDM': _lt('Redemption'),
    'SUBS': _lt('Subscription'),
    'CROS': _lt('Cross Trade'),
    'SWIC': _lt('Switch'),
    'REAA': _lt('Redemption Asset Allocation'),
    'SUAA': _lt('Subscription Asset Allocation'),
    'PRUD': _lt('Principal Pay-down/pay-up'),
    'TOUT': _lt('Transfer Out'),
    'TRIN': _lt('Transfer In'),
    'XCHC': _lt('Exchange Traded CCP'),
    'XCHG': _lt('Exchange Traded'),
    'XCHN': _lt('Exchange Traded Non-CCP'),
    'OTCC': _lt('OTC CCP'),
    'OTCG': _lt('OTC'),
    'OTCN': _lt('OTC Non-CCP'),
    'XCHC': _lt('Exchange Traded CCP'),  # Blocked Transactions & CSD Blocked Transactions
    'XCHG': _lt('Exchange Traded'),
    'XCHN': _lt('Exchange Traded Non-CCP'),
    'OTCC': _lt('OTC CCP'),
    'OTCG': _lt('OTC'),
    'OTCN': _lt('OTC Non-CCP'),
    'MARG': _lt('Margin Payments'),  # Collateral Management
    'TRPO': _lt('Triparty Repo'),
    'REPU': _lt('Repo'),
    'SECB': _lt('Securities Borrowing'),
    'SECL': _lt('Securities Lending'),
    'OPBC': _lt('Option broker owned collateral'),
    'OPCC': _lt('Option client owned collateral'),
    'FWBC': _lt('Forwards broker owned collateral'),
    'FWCC': _lt('Forwards client owned collateral'),
    'MGCC': _lt('Margin client owned cash collateral'),
    'SWBC': _lt('Swap broker owned collateral'),
    'EQCO': _lt('Equity mark client owned'),
    'EQBO': _lt('Equity mark broker owned'),
    'CMCO': _lt('Corporate mark client owned'),
    'CMBO': _lt('Corporate mark broker owned'),
    'SLBC': _lt('Lending Broker Owned Cash Collateral'),
    'SLCC': _lt('Lending Client Owned Cash Collateral'),
    'CPRB': _lt('Corporate Rebate'),
    'BIDS': _lt('Repurchase offer/Issuer Bid/Reverse Rights.'),  # Corporate Action & Custody
    'BONU': _lt('Bonus Issue/Capitalisation Issue'),
    'BPUT': _lt('Put Redemption'),
    'CAPG': _lt('Capital Gains Distribution'),
    'CONV': _lt('Conversion'),
    'DECR': _lt('Decrease in Value'),
    'DRAW': _lt('Drawing'),
    'DRIP': _lt('Dividend Reinvestment'),
    'DTCH': _lt('Dutch Auction'),
    'DVCA': _lt('Cash Dividend'),
    'DVOP': _lt('Dividend Option'),
    'EXOF': _lt('Exchange'),
    'EXRI': _lt('Call on intermediate securities'),
    'EXWA': _lt('Warrant Exercise/Warrant Conversion'),
    'INTR': _lt('Interest Payment'),
    'LIQU': _lt('Liquidation Dividend / Liquidation Payment'),
    'MCAL': _lt('Full Call / Early Redemption'),
    'MRGR': _lt('Merger'),
    'ODLT': _lt('Odd Lot Sale/Purchase'),
    'PCAL': _lt('Partial Redemption with reduction of nominal value'),
    'PRED': _lt('Partial Redemption Without Reduction of Nominal Value'),
    'PRII': _lt('Interest Payment with Principle'),
    'PRIO': _lt('Priority Issue'),
    'REDM': _lt('Final Maturity'),
    'RHTS': _lt('Rights Issue/Subscription Rights/Rights Offer'),
    'SHPR': _lt('Equity Premium Reserve'),
    'TEND': _lt('Tender'),
    'TREC': _lt('Tax Reclaim'),
    'RWPL': _lt('Redemption Withdrawing Plan'),
    'SSPL': _lt('Subscription Savings Plan'),
    'CSLI': _lt('Cash in lieu'),
    'CHAR': _lt('Charge/fees'),  # Miscellaneous Securities Operations
    'BKFE': _lt('Bank Fees'),
    'CLAI': _lt('Compensation/Claims'),
    'MNFE': _lt('Management Fees'),
    'OVCH': _lt('Overdraft Charge'),
    'TRFE': _lt('Transaction Fees'),
    'UNCO': _lt('Underwriting Commission'),
    'STAM': _lt('Stamp duty'),
    'WITH': _lt('Withholding Tax'),
    'BROK': _lt('Brokerage fee'),
    'PRIN': _lt('Interest Payment with Principle'),
    'TREC': _lt('Tax Reclaim'),
    'GEN1': _lt('Withdrawal/distribution'),
    'GEN2': _lt('Deposit/Contribution'),
    'ERWI': _lt('Borrowing fee'),
    'ERWA': _lt('Lending income'),
    'SWEP': _lt('Sweep'),
    'SWAP': _lt('Swap Payment'),
    'FUTU': _lt('Future Variation Margin'),
    'RESI': _lt('Futures Residual Amount'),
    'FUCO': _lt('Futures Commission'),
    'INFD': _lt('Fixed Deposit Interest Amount'),
    # Account Management Sub-Families
    'ACCO': _lt('Account Opening'),
    'ACCC': _lt('Account Closing'),
    'ACCT': _lt('Account Transfer'),
    'VALD': _lt('Value Date'),
    'BCKV': _lt('Back Value'),
    'YTDA': _lt('YTD Adjustment'),
    'FLTA': _lt('Float adjustment'),
    'ERTA': _lt('Exchange Rate Adjustment'),
    'PSTE': _lt('Posting Error'),
    # General
    'NTAV': _lt('Not available'),
    'OTHR': _lt('Other'),
    'MCOP': _lt('Miscellaneous Credit Operations'),
    'MDOP': _lt('Miscellaneous Debit Operations'),
    'FCTI': _lt('Fees, Commission , Taxes, Charges and Interest'),
}


def _generic_get(*nodes, xpath, namespaces, placeholder=None):
    if placeholder is not None:
        xpath = xpath.format(placeholder=placeholder)
    for node in nodes:
        item = node.xpath(xpath, namespaces=namespaces)
        if item:
            return item[0]
    return False

class CAMT:
    # These are pair of getters: (getter for the amount, getter for the amount's currency)
    _amount_getters = [
        (partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:Amt/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:AmtDtls/ns:CntrValAmt/ns:Amt/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:CntrValAmt/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:Amt/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:Amt/text()'), partial(_generic_get, xpath='ns:Amt/@Ccy')),
    ]

    _charges_getters = [
        (partial(_generic_get, xpath='ns:Chrgs/ns:Rcrd/ns:Amt/text()'), partial(_generic_get, xpath='ns:Chrgs/ns:Rcrd/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:Chrgs/ns:Amt/text()'), partial(_generic_get, xpath='ns:Chrgs/ns:Amt/@Ccy')),
    ]

    _amount_charges_getters = [
        (partial(_generic_get, xpath='ns:Amt/text()'), partial(_generic_get, xpath='ns:Amt/@Ccy')),
    ]

    # These are pair of getters: (getter for the exchange rate, getter for the target currency)
    _target_rate_getters = [
        (partial(_generic_get, xpath='ns:AmtDtls/ns:CntrValAmt/ns:CcyXchg/ns:XchgRate/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:CntrValAmt/ns:CcyXchg/ns:TrgtCcy/text()')),
        (partial(_generic_get, xpath='ns:AmtDtls/ns:CntrValAmt/ns:CcyXchg/ns:XchgRate/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:CntrValAmt/ns:CcyXchg/ns:SrcCcy/text()')),
    ]

    # These are pair of getters: (getter for the exchange rate, getter for the source currency)
    _source_rate_getters = [
        (partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:CcyXchg/ns:XchgRate/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:CcyXchg/ns:SrcCcy/text()')),
        (partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:CcyXchg/ns:XchgRate/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:CcyXchg/ns:SrcCcy/text()')),
        (partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:CcyXchg/ns:XchgRate/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:CcyXchg/ns:TrgtCcy/text()')),
        (partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:CcyXchg/ns:XchgRate/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:CcyXchg/ns:TrgtCcy/text()')),
    ]

    # These are pair of getters: (getter for the amount, getter for the amount's currency)
    _currency_amount_getters = [
        (partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:Amt/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:InstdAmt/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:NtryDtls/ns:TxDtls/ns:AmtDtls/ns:InstdAmt/ns:Amt/text()'), partial(_generic_get, xpath='ns:NtryDtls/ns:TxDtls/ns:AmtDtls/ns:InstdAmt/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:Amt/text()'), partial(_generic_get, xpath='ns:AmtDtls/ns:TxAmt/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:NtryDtls/ns:TxDtls/ns:AmtDtls/ns:TxAmt/ns:Amt/text()'), partial(_generic_get, xpath='ns:NtryDtls/ns:TxDtls/ns:AmtDtls/ns:TxAmt/ns:Amt/@Ccy')),
        (partial(_generic_get, xpath='ns:Amt/text()'), partial(_generic_get, xpath='ns:Amt/@Ccy')),
    ]
    _total_amount_getters = [
        (partial(_generic_get, xpath='ns:NtryDtls/ns:Btch/ns:TtlAmt/text()'), partial(_generic_get, xpath='ns:NtryDtls/ns:Btch/ns:TtlAmt/@Ccy'))
    ]

    # Start Balance
    #   OPBD : Opening Booked
    #   PRCD : Previous Closing Balance
    #   OPAV : Opening Available
    #   ITBD : Interim Booked (in the case of preceeding pagination)
    # These are pair of getters: (getter for the amount, getter for the sign)
    _start_balance_getters = [
        (partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='OPBD']/../../ns:Amt/text()"),
        partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='OPBD']/../../ns:CdtDbtInd/text()")),
        (partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='PRCD']/../../ns:Amt/text()"),
        partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='PRCD']/../../ns:CdtDbtInd/text()")),
        (partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='OPAV']/../../ns:Amt/text()"),
        partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='OPAV']/../../ns:CdtDbtInd/text()")),
        (partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='ITBD']/../../ns:Amt/text()"),
        partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='ITBD']/../../ns:CdtDbtInd/text()")),
    ]

    # Ending Balance
    #   CLBD : Closing Booked
    #   CLAV : Closing Available
    #   ITBD : Interim Booked
    # These are pair of getters: (getter for the amount, getter for the sign)
    _end_balance_getters = [
        (partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLBD']/../../ns:Amt/text()"),
        partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLBD']/../../ns:CdtDbtInd/text()")),
        (partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLAV']/../../ns:Amt/text()"),
        partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLAV']/../../ns:CdtDbtInd/text()")),
        (partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='ITBD']/../../ns:Amt/text()"),
        partial(_generic_get, xpath="ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='ITBD']/../../ns:CdtDbtInd/text()")),
    ]

    _get_credit_debit_indicator = partial(_generic_get,
        xpath='ns:CdtDbtInd/text()')

    _get_charges_credit_debit_indicator = partial(_generic_get,
        xpath='ns:Chrgs/ns:Rcrd/ns:CdtDbtInd/text()')

    _get_transaction_date = partial(_generic_get,
        xpath=('ns:ValDt/ns:Dt/text()'
            '| ns:BookgDt/ns:Dt/text()'
            '| ns:BookgDt/ns:DtTm/text()'))

    _get_statement_date = partial(_generic_get,
        xpath=("ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLBD']/../../ns:Dt/ns:Dt/text()"
            " | ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLBD']/../../ns:Dt/ns:DtTm/text()"
            " | ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLAV']/../../ns:Dt/ns:Dt/text()"
            " | ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='CLAV']/../../ns:Dt/ns:DtTm/text()"
            " | ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='ITBD']/../../ns:Dt/ns:Dt/text()"
            " | ns:Bal/ns:Tp/ns:CdOrPrtry[ns:Cd='ITBD']/../../ns:Dt/ns:DtTm/text()"
            ))

    _get_partner_name = partial(_generic_get,
        xpath=('.//ns:RltdPties/ns:Ultmt{placeholder}/ns:Nm/text()'
            ' | .//ns:RltdPties/ns:Ultmt{placeholder}/ns:Pty/ns:Nm/text()'
            ' | .//ns:RltdPties/ns:{placeholder}/ns:Nm/text()'
            ' | .//ns:RltdPties/ns:{placeholder}/ns:Pty/ns:Nm/text()'
            ))

    _get_account_number = partial(_generic_get,
        xpath=('.//ns:RltdPties/ns:{placeholder}Acct/ns:Id/ns:IBAN/text()'
            '| (.//ns:{placeholder}Acct/ns:Id/ns:Othr/ns:Id)[1]/text()'))

    _get_main_ref = partial(_generic_get,
        xpath='.//ns:RmtInf/ns:Strd/ns:{placeholder}RefInf/ns:Ref/text()')

    _get_other_ref = partial(_generic_get,
        xpath=('ns:AcctSvcrRef/text()'
            '| {placeholder}ns:Refs/ns:TxId/text()'
            '| {placeholder}ns:Refs/ns:InstrId/text()'
            '| {placeholder}ns:Refs/ns:EndToEndId/text()'
            '| {placeholder}ns:Refs/ns:MndtId/text()'
            '| {placeholder}ns:Refs/ns:ChqNb/text()'))

    _get_additional_entry_info = partial(_generic_get, xpath='ns:AddtlNtryInf/text()')
    _get_additional_text_info = partial(_generic_get, xpath='ns:AddtlTxInf/text()')
    _get_transaction_id = partial(_generic_get, xpath='ns:Refs/ns:TxId/text()')
    _get_instruction_id = partial(_generic_get, xpath='ns:Refs/ns:InstrId/text()')
    _get_end_to_end_id = partial(_generic_get, xpath='ns:Refs/ns:EndToEndId/text()')
    _get_mandate_id = partial(_generic_get, xpath='ns:Refs/ns:MndtId/text()')
    _get_check_number = partial(_generic_get, xpath='ns:Refs/ns:ChqNb/text()')

    @staticmethod
    def _get_signed_balance(node, namespaces, getters):
        for balance_getter, sign_getter in getters:
            balance = balance_getter(node, namespaces=namespaces)
            sign = sign_getter(node, namespaces=namespaces)
            if balance and sign:
                return -float(balance) if sign == 'DBIT'  else float(balance)
        return None

    @staticmethod
    def _get_signed_amount(*nodes, namespaces, journal_currency=None):
        def get_value_and_currency_name(node, getters, target_currency=None):
            for value_getter, currency_getter in getters:
                value = value_getter(node, namespaces=namespaces)
                currency_name = currency_getter(node, namespaces=namespaces)
                if value and (target_currency is None or currency_name == target_currency):
                    return float(value), currency_name
            return None, None

        def get_rate(*entries, target_currency, source_currency=None):
            for entry in entries:
                source_rate = get_value_and_currency_name(entry, CAMT._source_rate_getters)[0]
                target_rate = get_value_and_currency_name(entry, CAMT._target_rate_getters)[0]

                rate = source_rate or target_rate
                if rate:
                    # According to the camt.053 Swiss Payment Standards, the exchange rate should be divided by 100 if the
                    # currency is in YEN, SEK, DKK or NOK.
                    if target_currency == 'CHF' and source_currency in ('SEK', 'DKK', 'YEN', 'NOK'):
                        rate /= 100
                    elif not source_rate:
                        rate = 1 / rate
                    return rate
            return None

        def get_charges(*entries, target_currency=None):
            for entry in entries:
                charges = get_value_and_currency_name(entry, CAMT._charges_getters, target_currency=target_currency)[0]
                if charges:
                    sign = -1 if CAMT._get_charges_credit_debit_indicator(entry, namespaces=namespaces) == "DBIT" else 1
                    return sign * charges
            return None

        entry_details = nodes[0]
        entry = nodes[1] if len(nodes) > 1 else nodes[0]
        journal_currency_name = journal_currency.name if journal_currency else None
        entry_amount = get_value_and_currency_name(entry, CAMT._amount_charges_getters, target_currency=journal_currency_name)[0]
        entry_details_amount = get_value_and_currency_name(entry_details, CAMT._amount_charges_getters, target_currency=journal_currency_name)[0]

        charges = get_charges(entry_details, entry)
        getters = CAMT._amount_charges_getters if charges else CAMT._amount_getters
        amount, amount_currency_name = get_value_and_currency_name(entry_details, getters)

        if not amount or (charges and journal_currency and journal_currency.compare_amounts(amount + charges, entry_amount) == 0):
            amount, amount_currency_name = get_value_and_currency_name(entry, getters)

        entry_amount_in_currency = get_value_and_currency_name(entry, getters, target_currency=amount_currency_name)[0]
        entry_details_amount_in_currency = get_value_and_currency_name(entry_details, getters, target_currency=amount_currency_name)[0]

        if not journal_currency or amount_currency_name == journal_currency_name:
            rate = 1.0
        else:
            rate = get_rate(entry_details, entry, target_currency=journal_currency_name, source_currency=amount_currency_name)
            entry_amount = entry_details_amount or entry_amount
            if entry_details_amount:
                entry_amount_in_currency = entry_details_amount_in_currency
            elif not entry_amount_in_currency:
                entry_amount_in_currency = amount
            computed_rate = entry_amount / entry_amount_in_currency
            if rate:
                if float_compare(rate, computed_rate, precision_digits=4) == 0:
                    rate = computed_rate
                elif float_compare(rate, 1 / computed_rate, precision_digits=4) == 0:
                    rate = 1 / computed_rate
            else:
                amount, amount_currency_name = get_value_and_currency_name(entry_details, CAMT._amount_getters, target_currency=journal_currency_name)
                if not amount:
                    amount, amount_currency_name = get_value_and_currency_name(entry, CAMT._amount_getters, target_currency=journal_currency_name)
                if amount_currency_name == journal_currency_name:
                    rate = 1.0
            if not rate:
                raise ValidationError(_lt("No exchange rate was found to convert an amount into the currency of the journal"))

        sign = 1 if CAMT._get_credit_debit_indicator(*nodes, namespaces=namespaces) == "CRDT" else -1
        total_amount, total_amount_currency = get_value_and_currency_name(entry, CAMT._total_amount_getters)
        result_amount = sign * amount * rate
        if not total_amount or total_amount_currency != journal_currency_name and journal_currency:
            entry_amount = entry_details_amount or entry_amount
            total_amount = total_amount or amount
            if journal_currency.compare_amounts(total_amount * rate, entry_amount) == 0:
                result_amount = sign * amount * rate
            elif journal_currency.compare_amounts(total_amount / rate, entry_amount) == 0:
                result_amount = sign * amount / rate

        if journal_currency:
            result_amount = journal_currency.round(result_amount)
        return result_amount

    @staticmethod
    def _get_counter_party(*nodes, namespaces):
        ind = CAMT._get_credit_debit_indicator(*nodes, namespaces=namespaces)
        return 'Dbtr' if ind == 'CRDT' else 'Cdtr'

    @staticmethod
    def _set_amount_in_currency(node, getters, entry_vals, currency, curr_cache, has_multi_currency, namespaces):
        for value_getter, currency_getter in getters:
            instruc_amount = value_getter(node, namespaces=namespaces)
            instruc_curr = currency_getter(node, namespaces=namespaces)
            if (has_multi_currency and instruc_amount and instruc_curr and
                    instruc_curr != currency and instruc_curr in curr_cache):
                entry_vals['amount_currency'] = math.copysign(abs(float(instruc_amount)), entry_vals['amount'])
                entry_vals['foreign_currency_id'] = curr_cache[instruc_curr]
                break

    @staticmethod
    def _get_transaction_name(node, namespaces, entry=None):
        xpaths = (
            './/ns:RmtInf/ns:Ustrd/text()',
            './/ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref/text()',
            './/ns:AddtlNtryInf/text()',
            './/ns:RmtInf/ns:Strd/ns:AddtlRmtInf/text()',
        )
        for xpath in xpaths:
            if entry is not None and 'AddtlNtryInf' in xpath:
                transaction_name = entry.xpath(xpath, namespaces=namespaces)
            else:
                transaction_name = node.xpath(xpath, namespaces=namespaces)
            if transaction_name:
                return ' '.join(transaction_name)
        return '/'

    @staticmethod
    def _get_ref(node, counter_party, prefix, namespaces):
        ref = CAMT._get_main_ref(node, placeholder=counter_party, namespaces=namespaces)
        if ref is False:  # Explicitely match False, not a falsy value
            ref = CAMT._get_other_ref(node, placeholder=prefix, namespaces=namespaces)
        return ref

    @staticmethod
    def _get_unique_import_id(entry, sequence, name, date, unique_import_set, namespaces):
        unique_import_ref = entry.xpath('ns:AcctSvcrRef/text()', namespaces=namespaces)
        if unique_import_ref and not CAMT._is_full_of_zeros(unique_import_ref[0]) and unique_import_ref[0] != 'NOTPROVIDED':
            entry_ref = entry.xpath('ns:NtryRef/text()', namespaces=namespaces)
            if entry_ref:
                return '{}-{}-{}'.format(name, unique_import_ref[0], entry_ref[0])
            elif not entry_ref and unique_import_ref[0] not in unique_import_set:
                return unique_import_ref[0]
            else:
                return '{}-{}-{}'.format(name, unique_import_ref[0], sequence)
        else:
            return '{}-{}-{}'.format(name, date, sequence)

    @staticmethod
    def _get_transaction_type(node, namespaces):
        code = node.xpath('ns:Domn/ns:Cd/text()', namespaces=namespaces)
        family = node.xpath('ns:Domn/ns:Fmly/ns:Cd/text()', namespaces=namespaces)
        subfamily = node.xpath('ns:Domn/ns:Fmly/ns:SubFmlyCd/text()', namespaces=namespaces)
        if code:
            return {'transaction_type': "{code}: {family} ({subfamily})".format(
                code=codes.get(code[0].upper(), code[0]),
                family=family and codes.get(family[0].upper(), family[0]) or '',
                subfamily=subfamily and codes.get(subfamily[0].upper(), subfamily[0]) or '',
            )}
        return {}

    @staticmethod
    def _get_partner_address(node, ns, ph):
        StrtNm = node.xpath('ns:RltdPties/ns:{}/ns:PstlAdr/ns:StrtNm/text()'.format(ph), namespaces=ns)
        BldgNb = node.xpath('ns:RltdPties/ns:{}/ns:PstlAdr/ns:BldgNb/text()'.format(ph), namespaces=ns)
        PstCd = node.xpath('ns:RltdPties/ns:{}/ns:PstlAdr/ns:PstCd/text()'.format(ph), namespaces=ns)
        TwnNm = node.xpath('ns:RltdPties/ns:{}/ns:PstlAdr/ns:TwnNm/text()'.format(ph), namespaces=ns)
        Ctry = node.xpath('ns:RltdPties/ns:{}/ns:PstlAdr/ns:Ctry/text()'.format(ph), namespaces=ns)
        AdrLine = node.xpath('ns:RltdPties/ns:{}/ns:PstlAdr/ns:AdrLine/text()'.format(ph), namespaces=ns)
        address = "\n".join(AdrLine)
        if StrtNm:
            address = "\n".join([address, ", ".join(StrtNm + BldgNb)])
        if PstCd or TwnNm:
            address = "\n".join([address, " ".join(PstCd + TwnNm)])
        if Ctry:
            address = "\n".join([address, Ctry[0]])
        return address

    @staticmethod
    def _is_full_of_zeros(strg):
        pattern_zero = re.compile('^0+$')
        return bool(pattern_zero.match(strg))
