from __future__ import absolute_import

import sys
import decimal
import datetime
import codecs
import re
import collections
import contextlib

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

import six
from . import mcc

odict = collections

try:
    from bs4 import BeautifulSoup

    def soup_maker(fh):
        return BeautifulSoup(fh, 'html.parser')
except ImportError:
    from BeautifulSoup import BeautifulStoneSoup
    soup_maker = BeautifulStoneSoup


def try_decode(string, encoding):
    if hasattr(string, 'decode'):
        string = string.decode(encoding)
    return string


def is_iterable(candidate):
    if sys.version_info < (2, 6):
        return hasattr(candidate, 'next')
    return isinstance(candidate, Iterable)


@contextlib.contextmanager
def save_pos(fh):
    """
    Save the position of the file handle, seek to the beginning, and
    then restore the position.
    """
    orig_pos = fh.tell()
    fh.seek(0)
    try:
        yield fh
    finally:
        fh.seek(orig_pos)


class OfxFile(object):
    def __init__(self, fh):
        """
        fh should be a seekable file-like byte stream object
        """
        self.headers = odict.OrderedDict()
        self.fh = fh

        if not is_iterable(self.fh):
            return
        if not hasattr(self.fh, "seek"):
            return  # fh is not a file object, we're doomed.

        # If the file handler is text stream, convert to bytes one:
        first = self.fh.read(1)
        self.fh.seek(0)
        if not isinstance(first, bytes):
            self.fh = six.BytesIO(six.b(self.fh.read()))

        with save_pos(self.fh):
            self.read_headers()
            self.handle_encoding()
            self.replace_NONE_headers()

    def read_headers(self):
        head_data = self.fh.read(1024 * 10)
        head_data = head_data[:head_data.find(six.b('<'))]

        for line in head_data.splitlines():
            # Newline?
            if line.strip() == six.b(""):
                break

            header, value = line.split(six.b(":"))
            header, value = header.strip().upper(), value.strip()

            self.headers[header] = value

    def handle_encoding(self):
        """
        Decode the headers and wrap self.fh in a decoder such that it
        subsequently returns only text.
        """
        # decode the headers using ascii
        ascii_headers = odict.OrderedDict(
            (
                key.decode('ascii', 'replace'),
                value.decode('ascii', 'replace'),
            )
            for key, value in six.iteritems(self.headers)
        )

        enc_type = ascii_headers.get('ENCODING')

        if not enc_type:
            # no encoding specified, use the ascii-decoded headers
            self.headers = ascii_headers
            # decode the body as ascii as well
            self.fh = codecs.lookup('ascii').streamreader(self.fh)
            return

        if enc_type == "USASCII":
            cp = ascii_headers.get("CHARSET", "1252")
            if cp == "8859-1":
                encoding = "iso-8859-1"
            else:
                encoding = "cp%s" % (cp, )

        elif enc_type in ("UNICODE", "UTF-8"):
            encoding = "utf-8"

        codec = codecs.lookup(encoding)

        self.fh = codec.streamreader(self.fh)

        # Decode the headers using the encoding
        self.headers = odict.OrderedDict(
            (key.decode(encoding), value.decode(encoding))
            for key, value in six.iteritems(self.headers)
        )

    def replace_NONE_headers(self):
        """
        Any headers that indicate 'none' should be replaced with Python
        None values
        """
        for header in self.headers:
            if self.headers[header].upper() == 'NONE':
                self.headers[header] = None


class OfxPreprocessedFile(OfxFile):
    def __init__(self, fh):
        super(OfxPreprocessedFile, self).__init__(fh)

        if self.fh is None:
            return

        ofx_string = self.fh.read()

        # find all closing tags as hints
        closing_tags = [t.upper() for t in re.findall(r'(?i)</([a-z0-9_\.]+)>',
                                                      ofx_string)]

        # close all tags that don't have closing tags and
        # leave all other data intact
        last_open_tag = None
        tokens = re.split(r'(?i)(</?[a-z0-9_\.]+>)', ofx_string)
        new_fh = StringIO()
        for token in tokens:
            is_closing_tag = token.startswith('</')
            is_processing_tag = token.startswith('<?')
            is_cdata = token.startswith('<!')
            is_tag = token.startswith('<') and not is_cdata
            is_open_tag = is_tag and not is_closing_tag \
                and not is_processing_tag
            if is_tag:
                if last_open_tag is not None:
                    new_fh.write("</%s>" % last_open_tag)
                    last_open_tag = None
            if is_open_tag:
                tag_name = re.findall(r'(?i)<([a-z0-9_\.]+)>', token)[0]
                if tag_name.upper() not in closing_tags:
                    last_open_tag = tag_name
            new_fh.write(token)
        new_fh.seek(0)
        self.fh = new_fh


class Ofx(object):
    def __str__(self):
        return ""
#        headers = "\r\n".join(":".join(el if el else "NONE" for el in item)
#        for item in six.iteritems(self.headers))
#        headers += "\r\n\r\n"
#
#        return headers + str(self.signon)


class AccountType(object):
    (Unknown, Bank, CreditCard, Investment) = range(0, 4)


class Account(object):
    def __init__(self):
        self.curdef = None
        self.statement = None
        self.account_id = ''
        self.routing_number = ''
        self.branch_id = ''
        self.account_type = ''
        self.institution = None
        self.type = AccountType.Unknown
        # Used for error tracking
        self.warnings = []

    @property
    def number(self):
        # For backwards compatibility.  Remove in version 1.0.
        return self.account_id


class InvestmentAccount(Account):
    def __init__(self):
        super(InvestmentAccount, self).__init__()
        self.brokerid = ''


class BrokerageBalance:
    def __init__(self):
        self.name = None
        self.description = None
        self.value = None  # decimal


class Security:
    def __init__(self, uniqueid, name, ticker, memo):
        self.uniqueid = uniqueid
        self.name = name
        self.ticker = ticker
        self.memo = memo


class Signon:
    def __init__(self, keys):
        self.code = keys['code']
        self.severity = keys['severity']
        self.message = keys['message']
        self.dtserver = keys['dtserver']
        self.language = keys['language']
        self.dtprofup = keys['dtprofup']
        self.fi_org = keys['org']
        self.fi_fid = keys['fid']
        self.intu_bid = keys['intu.bid']

        if int(self.code) == 0:
            self.success = True
        else:
            self.success = False

    def __str__(self):
        ret = "\t<SIGNONMSGSRSV1>\r\n" + "\t\t<SONRS>\r\n" + \
              "\t\t\t<STATUS>\r\n"
        ret += "\t\t\t\t<CODE>%s\r\n" % self.code
        ret += "\t\t\t\t<SEVERITY>%s\r\n" % self.severity
        if self.message:
            ret += "\t\t\t\t<MESSAGE>%s\r\n" % self.message
        ret += "\t\t\t</STATUS>\r\n"
        if self.dtserver is not None:
            ret += "\t\t\t<DTSERVER>" + self.dtserver + "\r\n"
        if self.language is not None:
            ret += "\t\t\t<LANGUAGE>" + self.language + "\r\n"
        if self.dtprofup is not None:
            ret += "\t\t\t<DTPROFUP>" + self.dtprofup + "\r\n"
        if (self.fi_org is not None) or (self.fi_fid is not None):
            ret += "\t\t\t<FI>\r\n"
            if self.fi_org is not None:
                ret += "\t\t\t\t<ORG>" + self.fi_org + "\r\n"
            if self.fi_fid is not None:
                ret += "\t\t\t\t<FID>" + self.fi_fid + "\r\n"
            ret += "\t\t\t</FI>\r\n"
        if self.intu_bid is not None:
            ret += "\t\t\t<INTU.BID>" + self.intu_bid + "\r\n"
        ret += "\t\t</SONRS>\r\n"
        ret += "\t</SIGNONMSGSRSV1>\r\n"
        return ret


class Statement(object):
    def __init__(self):
        self.start_date = ''
        self.end_date = ''
        self.currency = ''
        self.transactions = []
        # Error tracking:
        self.discarded_entries = []
        self.warnings = []


class InvestmentStatement(object):
    def __init__(self):
        self.positions = []
        self.transactions = []
        # Error tracking:
        self.discarded_entries = []
        self.warnings = []


class Transaction(object):
    def __init__(self):
        self.payee = ''
        self.type = ''
        self.date = None
        self.user_date = None
        self.amount = None
        self.id = ''
        self.memo = ''
        self.sic = None
        self.mcc = ''
        self.checknum = ''

    def __repr__(self):
        return "<Transaction units=" + str(self.amount) + ">"


class InvestmentTransaction(object):
    AGGREGATE_TYPES = ['buydebt', 'buymf', 'buyopt', 'buyother',
                       'buystock', 'closureopt', 'income',
                       'invexpense', 'jrnlfund', 'jrnlsec',
                       'margininterest', 'reinvest', 'retofcap',
                       'selldebt', 'sellmf', 'sellopt', 'sellother',
                       'sellstock', 'split', 'transfer']

    def __init__(self, type):
        self.type = type.lower()
        self.tradeDate = None
        self.settleDate = None
        self.memo = ''
        self.security = ''
        self.income_type = ''
        self.units = decimal.Decimal(0)
        self.unit_price = decimal.Decimal(0)
        self.commission = decimal.Decimal(0)
        self.fees = decimal.Decimal(0)
        self.total = decimal.Decimal(0)
        self.tferaction = None

    def __repr__(self):
        return "<InvestmentTransaction type=" + str(self.type) + ", \
            units=" + str(self.units) + ">"


class Position(object):
    def __init__(self):
        self.security = ''
        self.units = decimal.Decimal(0)
        self.unit_price = decimal.Decimal(0)
        self.market_value = decimal.Decimal(0)


class Institution(object):
    def __init__(self):
        self.organization = ''
        self.fid = ''


class OfxParserException(Exception):
    pass


class OfxParser(object):
    @classmethod
    def parse(cls, file_handle, fail_fast=True, custom_date_format=None):
        '''
        parse is the main entry point for an OfxParser. It takes a file
        handle and an optional log_errors flag.

        If fail_fast is True, the parser will fail on any errors.
        If fail_fast is False, the parser will log poor statements in the
        statement class and continue to run. Note: the library does not
        guarantee that no exceptions will be raised to the caller, only
        that statements will include bad transactions (which are marked).

        '''
        cls.fail_fast = fail_fast
        cls.custom_date_format = custom_date_format

        if not hasattr(file_handle, 'seek'):
            raise TypeError(six.u('parse() accepts a seek-able file handle\
                            , not %s' % type(file_handle).__name__))

        ofx_obj = Ofx()

        # Store the headers
        ofx_file = OfxPreprocessedFile(file_handle)
        ofx_obj.headers = ofx_file.headers
        ofx_obj.accounts = []
        ofx_obj.signon = None

        ofx = soup_maker(ofx_file.fh)
        if ofx.find('ofx') is None:
            raise OfxParserException('The ofx file is empty!')

        sonrs_ofx = ofx.find('sonrs')
        if sonrs_ofx:
            ofx_obj.signon = cls.parseSonrs(sonrs_ofx)

        stmttrnrs = ofx.find('stmttrnrs')
        if stmttrnrs:
            stmttrnrs_trnuid = stmttrnrs.find('trnuid')
            if stmttrnrs_trnuid:
                ofx_obj.trnuid = stmttrnrs_trnuid.contents[0].strip()

            stmttrnrs_status = stmttrnrs.find('status')
            if stmttrnrs_status:
                ofx_obj.status = {}
                ofx_obj.status['code'] = int(
                    stmttrnrs_status.find('code').contents[0].strip()
                )
                ofx_obj.status['severity'] = \
                    stmttrnrs_status.find('severity').contents[0].strip()
                message = stmttrnrs_status.find('message')
                ofx_obj.status['message'] = \
                    message.contents[0].strip() if message else None

        ccstmttrnrs = ofx.find('ccstmttrnrs')
        if ccstmttrnrs:
            ccstmttrnrs_trnuid = ccstmttrnrs.find('trnuid')
            if ccstmttrnrs_trnuid:
                ofx_obj.trnuid = ccstmttrnrs_trnuid.contents[0].strip()

            ccstmttrnrs_status = ccstmttrnrs.find('status')
            if ccstmttrnrs_status:
                ofx_obj.status = {}
                ofx_obj.status['code'] = int(
                    ccstmttrnrs_status.find('code').contents[0].strip()
                )
                ofx_obj.status['severity'] = \
                    ccstmttrnrs_status.find('severity').contents[0].strip()
                message = ccstmttrnrs_status.find('message')
                ofx_obj.status['message'] = \
                    message.contents[0].strip() if message else None

        stmtrs_ofx = ofx.findAll('stmtrs')
        if stmtrs_ofx:
            ofx_obj.accounts += cls.parseStmtrs(stmtrs_ofx, AccountType.Bank)

        ccstmtrs_ofx = ofx.findAll('ccstmtrs')
        if ccstmtrs_ofx:
            ofx_obj.accounts += cls.parseStmtrs(
                ccstmtrs_ofx, AccountType.CreditCard)

        invstmtrs_ofx = ofx.findAll('invstmtrs')
        if invstmtrs_ofx:
            ofx_obj.accounts += cls.parseInvstmtrs(invstmtrs_ofx)
            seclist_ofx = ofx.find('seclist')
            if seclist_ofx:
                ofx_obj.security_list = cls.parseSeclist(seclist_ofx)
            else:
                ofx_obj.security_list = None

        acctinfors_ofx = ofx.find('acctinfors')
        if acctinfors_ofx:
            ofx_obj.accounts += cls.parseAcctinfors(acctinfors_ofx, ofx)

        fi_ofx = ofx.find('fi')
        if fi_ofx:
            for account in ofx_obj.accounts:
                account.institution = cls.parseOrg(fi_ofx)

        if ofx_obj.accounts:
            ofx_obj.account = ofx_obj.accounts[0]

        return ofx_obj

    @classmethod
    def parseOfxDateTime(cls, ofxDateTime):
        # dateAsString looks something like 20101106160000.00[-5:EST]
        # for 6 Nov 2010 4pm UTC-5 aka EST

        # Some places (e.g. Newfoundland) have non-integer offsets.
        res = re.search(r"\[(?P<tz>[-+]?\d+\.?\d*)\:\w*\]$", ofxDateTime)
        if res:
            tz = float(res.group('tz'))
        else:
            tz = 0

        timeZoneOffset = datetime.timedelta(hours=tz)

        res = re.search(r"^[0-9]*\.([0-9]{0,5})", ofxDateTime)
        if res:
            msec = datetime.timedelta(seconds=float("0." + res.group(1)))
        else:
            msec = datetime.timedelta(seconds=0)

        try:
            local_date = datetime.datetime.strptime(ofxDateTime[:14], '%Y%m%d%H%M%S')
            return local_date - timeZoneOffset + msec
        except ValueError:
            if ofxDateTime[:8] == "00000000":
                return None

            if not cls.custom_date_format:
                return datetime.datetime.strptime(
                    ofxDateTime[:8], '%Y%m%d') - timeZoneOffset + msec
            else:
                return datetime.datetime.strptime(
                    ofxDateTime[:8], cls.custom_date_format) - timeZoneOffset + msec

    @classmethod
    def parseAcctinfors(cls, acctinfors_ofx, ofx):
        all_accounts = []
        for i in acctinfors_ofx.findAll('acctinfo'):
            accounts = []
            if i.find('invacctinfo'):
                accounts += cls.parseInvstmtrs([i])
            elif i.find('ccacctinfo'):
                accounts += cls.parseStmtrs([i], AccountType.CreditCard)
            elif i.find('bankacctinfo'):
                accounts += cls.parseStmtrs([i], AccountType.Bank)
            else:
                continue

            fi_ofx = ofx.find('fi')
            if fi_ofx:
                for account in all_accounts:
                    account.institution = cls.parseOrg(fi_ofx)

            desc = i.find('desc')
            if hasattr(desc, 'contents'):
                for account in accounts:
                    account.desc = desc.contents[0].strip()
            all_accounts += accounts
        return all_accounts

    @classmethod
    def parseInvstmtrs(cls, invstmtrs_list):
        ret = []
        for invstmtrs_ofx in invstmtrs_list:
            account = InvestmentAccount()
            acctid_tag = invstmtrs_ofx.find('acctid')
            if hasattr(acctid_tag, 'contents'):
                try:
                    account.account_id = acctid_tag.contents[0].strip()
                except IndexError:
                    account.warnings.append(
                        six.u("Empty acctid tag for %s") % invstmtrs_ofx)
                    if cls.fail_fast:
                        raise

            brokerid_tag = invstmtrs_ofx.find('brokerid')
            if hasattr(brokerid_tag, 'contents'):
                try:
                    account.brokerid = brokerid_tag.contents[0].strip()
                except IndexError:
                    account.warnings.append(
                        six.u("Empty brokerid tag for %s") % invstmtrs_ofx)
                    if cls.fail_fast:
                        raise

            account.type = AccountType.Investment

            if invstmtrs_ofx:
                account.statement = cls.parseInvestmentStatement(
                    invstmtrs_ofx)
            ret.append(account)
        return ret

    @classmethod
    def parseSeclist(cls, seclist_ofx):
        securityList = []
        for secinfo_ofx in seclist_ofx.findAll('secinfo'):
            uniqueid_tag = secinfo_ofx.find('uniqueid')
            name_tag = secinfo_ofx.find('secname')
            ticker_tag = secinfo_ofx.find('ticker')
            memo_tag = secinfo_ofx.find('memo')
            if uniqueid_tag and name_tag:
                try:
                    ticker = ticker_tag.contents[0].strip()
                except AttributeError:
                    # ticker can be empty
                    ticker = None
                try:
                    memo = memo_tag.contents[0].strip()
                except AttributeError:
                    # memo can be empty
                    memo = None
                securityList.append(
                    Security(uniqueid_tag.contents[0].strip(),
                             name_tag.contents[0].strip(),
                             ticker,
                             memo))
        return securityList

    @classmethod
    def parseInvestmentPosition(cls, ofx):
        position = Position()
        tag = ofx.find('uniqueid')
        if hasattr(tag, 'contents'):
            position.security = tag.contents[0].strip()
        tag = ofx.find('units')
        if hasattr(tag, 'contents'):
            position.units = cls.toDecimal(tag)
        tag = ofx.find('unitprice')
        if hasattr(tag, 'contents'):
            position.unit_price = cls.toDecimal(tag)
        tag = ofx.find('mktval')
        if hasattr(tag, 'contents'):
            position.market_value = cls.toDecimal(tag)
        tag = ofx.find('dtpriceasof')
        if hasattr(tag, 'contents'):
            try:
                position.date = cls.parseOfxDateTime(tag.contents[0].strip())
            except ValueError:
                raise
        return position

    @classmethod
    def parseInvestmentTransaction(cls, ofx):
        transaction = InvestmentTransaction(ofx.name)
        tag = ofx.find('fitid')
        if hasattr(tag, 'contents'):
            transaction.id = tag.contents[0].strip()
        tag = ofx.find('memo')
        if hasattr(tag, 'contents'):
            transaction.memo = tag.contents[0].strip()
        tag = ofx.find('dttrade')
        if hasattr(tag, 'contents'):
            try:
                transaction.tradeDate = cls.parseOfxDateTime(
                    tag.contents[0].strip())
            except ValueError:
                raise
        tag = ofx.find('dtsettle')
        if hasattr(tag, 'contents'):
            try:
                transaction.settleDate = cls.parseOfxDateTime(
                    tag.contents[0].strip())
            except ValueError:
                raise
        tag = ofx.find('uniqueid')
        if hasattr(tag, 'contents'):
            transaction.security = tag.contents[0].strip()
        tag = ofx.find('incometype')
        if hasattr(tag, 'contents'):
            transaction.income_type = tag.contents[0].strip()
        tag = ofx.find('units')
        if hasattr(tag, 'contents'):
            transaction.units = cls.toDecimal(tag)
        tag = ofx.find('unitprice')
        if hasattr(tag, 'contents'):
            transaction.unit_price = cls.toDecimal(tag)
        tag = ofx.find('commission')
        if hasattr(tag, 'contents'):
            transaction.commission = cls.toDecimal(tag)
        tag = ofx.find('fees')
        if hasattr(tag, 'contents'):
            transaction.fees = cls.toDecimal(tag)
        tag = ofx.find('total')
        if hasattr(tag, 'contents'):
            transaction.total = cls.toDecimal(tag)
        tag = ofx.find('inv401ksource')
        if hasattr(tag, 'contents'):
            transaction.inv401ksource = tag.contents[0].strip()
        tag = ofx.find('tferaction')
        if hasattr(tag, 'contents'):
            transaction.tferaction = tag.contents[0].strip()
        return transaction

    @classmethod
    def parseInvestmentStatement(cls, invstmtrs_ofx):
        statement = InvestmentStatement()
        currency_tag = invstmtrs_ofx.find('curdef')
        if hasattr(currency_tag, "contents"):
            statement.currency = currency_tag.contents[0].strip().lower()
        invtranlist_ofx = invstmtrs_ofx.find('invtranlist')
        if invtranlist_ofx is not None:
            tag = invtranlist_ofx.find('dtstart')
            if hasattr(tag, 'contents'):
                try:
                    statement.start_date = cls.parseOfxDateTime(
                        tag.contents[0].strip())
                except IndexError:
                    statement.warnings.append(six.u('Empty start date.'))
                    if cls.fail_fast:
                        raise
                except ValueError:
                    e = sys.exc_info()[1]
                    statement.warnings.append(six.u('Invalid start date:\
                        %s') % e)
                    if cls.fail_fast:
                        raise

            tag = invtranlist_ofx.find('dtend')
            if hasattr(tag, 'contents'):
                try:
                    statement.end_date = cls.parseOfxDateTime(
                        tag.contents[0].strip())
                except IndexError:
                    statement.warnings.append(six.u('Empty end date.'))
                except ValueError:
                    e = sys.exc_info()[1]
                    statement.warnings.append(six.u('Invalid end date: \
                        %s') % e)
                    if cls.fail_fast:
                        raise

        for transaction_type in ['posmf', 'posstock', 'posopt', 'posother',
                                 'posdebt']:
            try:
                for investment_ofx in invstmtrs_ofx.findAll(transaction_type):
                    statement.positions.append(
                        cls.parseInvestmentPosition(investment_ofx))
            except (ValueError, IndexError, decimal.InvalidOperation,
                    TypeError):
                e = sys.exc_info()[1]
                if cls.fail_fast:
                    raise
                statement.discarded_entries.append(
                    {six.u('error'): six.u("Error parsing positions: \
                        ") + str(e), six.u('content'): investment_ofx}
                )

        for transaction_type in InvestmentTransaction.AGGREGATE_TYPES:
            try:
                for investment_ofx in invstmtrs_ofx.findAll(transaction_type):
                    statement.transactions.append(
                        cls.parseInvestmentTransaction(investment_ofx))
            except (ValueError, IndexError, decimal.InvalidOperation):
                e = sys.exc_info()[1]
                if cls.fail_fast:
                    raise
                statement.discarded_entries.append(
                    {six.u('error'): transaction_type + ": " + str(e),
                     six.u('content'): investment_ofx}
                )

        for transaction_ofx in invstmtrs_ofx.findAll('invbanktran'):
            for stmt_ofx in transaction_ofx.findAll('stmttrn'):
                try:
                    statement.transactions.append(
                        cls.parseTransaction(stmt_ofx))
                except OfxParserException:
                    ofxError = sys.exc_info()[1]
                    statement.discarded_entries.append(
                        {'error': str(ofxError), 'content': transaction_ofx})
                    if cls.fail_fast:
                        raise

        invbal_ofx = invstmtrs_ofx.find('invbal')
        if invbal_ofx is not None:
            # <AVAILCASH>18073.98<MARGINBALANCE>+00000000000.00<SHORTBALANCE>+00000000000.00<BUYPOWER>+00000000000.00
            availcash_ofx = invbal_ofx.find('availcash')
            if availcash_ofx is not None:
                statement.available_cash = cls.toDecimal(availcash_ofx)
            margin_balance_ofx = invbal_ofx.find('marginbalance')
            if margin_balance_ofx is not None:
                statement.margin_balance = cls.toDecimal(margin_balance_ofx)
            short_balance_ofx = invbal_ofx.find('shortbalance')
            if short_balance_ofx is not None:
                statement.short_balance = cls.toDecimal(short_balance_ofx)
            buy_power_ofx = invbal_ofx.find('buypower')
            if buy_power_ofx is not None:
                statement.buy_power = cls.toDecimal(buy_power_ofx)

            ballist_ofx = invbal_ofx.find('ballist')
            if ballist_ofx is not None:
                statement.balance_list = []
                for balance_ofx in ballist_ofx.findAll('bal'):
                    brokerage_balance = BrokerageBalance()
                    name_ofx = balance_ofx.find('name')
                    if name_ofx is not None:
                        brokerage_balance.name = name_ofx.contents[0].strip()
                    description_ofx = balance_ofx.find('desc')
                    if description_ofx is not None:
                        brokerage_balance.description = \
                            description_ofx.contents[0].strip()
                    value_ofx = balance_ofx.find('value')
                    if value_ofx is not None:
                        brokerage_balance.value = cls.toDecimal(value_ofx)
                    statement.balance_list.append(brokerage_balance)

        return statement

    @classmethod
    def parseOrg(cls, fi_ofx):
        institution = Institution()
        org = fi_ofx.find('org')
        if hasattr(org, 'contents'):
            institution.organization = org.contents[0].strip()

        fid = fi_ofx.find('fid')
        if hasattr(fid, 'contents'):
            institution.fid = fid.contents[0].strip()

        return institution

    @classmethod
    def parseSonrs(cls, sonrs):

        items = [
            'code',
            'severity',
            'dtserver',
            'language',
            'dtprofup',
            'org',
            'fid',
            'intu.bid',
            'message'
        ]
        idict = {}
        for i in items:
            try:
                idict[i] = sonrs.find(i).contents[0].strip()
            except Exception:
                idict[i] = None
        idict['code'] = int(idict['code'])
        if idict['message'] is None:
            idict['message'] = ''

        return Signon(idict)

    @classmethod
    def parseStmtrs(cls, stmtrs_list, accountType):
        ''' Parse the <STMTRS> tags and return a list of Accounts object. '''
        ret = []
        for stmtrs_ofx in stmtrs_list:
            account = Account()
            act_curdef = stmtrs_ofx.find('curdef')
            if act_curdef and act_curdef.contents:
                account.curdef = act_curdef.contents[0].strip()
            acctid_tag = stmtrs_ofx.find('acctid')
            if acctid_tag and acctid_tag.contents:
                account.account_id = acctid_tag.contents[0].strip()
            bankid_tag = stmtrs_ofx.find('bankid')
            if bankid_tag and bankid_tag.contents:
                account.routing_number = bankid_tag.contents[0].strip()
            branchid_tag = stmtrs_ofx.find('branchid')
            if branchid_tag and branchid_tag.contents:
                account.branch_id = branchid_tag.contents[0].strip()
            type_tag = stmtrs_ofx.find('accttype')
            if type_tag and type_tag.contents:
                account.account_type = type_tag.contents[0].strip()
            account.type = accountType

            if stmtrs_ofx:
                account.statement = cls.parseStatement(stmtrs_ofx)
            ret.append(account)
        return ret

    @classmethod
    def parseBalance(cls, statement, stmt_ofx, bal_tag_name, bal_attr,
                     bal_date_attr, bal_type_string):
        bal_tag = stmt_ofx.find(bal_tag_name)
        if hasattr(bal_tag, "contents"):
            balamt_tag = bal_tag.find('balamt')
            dtasof_tag = bal_tag.find('dtasof')
            if hasattr(balamt_tag, "contents"):
                try:
                    setattr(statement, bal_attr, cls.toDecimal(balamt_tag))
                except (IndexError, decimal.InvalidOperation):
                    statement.warnings.append(
                        six.u("%s balance amount was empty for \
                            %s") % (bal_type_string, stmt_ofx))
                    if cls.fail_fast:
                        raise OfxParserException("Empty %s balance\
                            " % bal_type_string)
            if hasattr(dtasof_tag, "contents"):
                try:
                    setattr(statement, bal_date_attr, cls.parseOfxDateTime(
                        dtasof_tag.contents[0].strip()))
                except IndexError:
                    statement.warnings.append(
                        six.u("%s balance date was empty for %s\
                            ") % (bal_type_string, stmt_ofx))
                    if cls.fail_fast:
                        raise
                except ValueError:
                    statement.warnings.append(
                        six.u("%s balance date was not allowed for \
                            %s") % (bal_type_string, stmt_ofx))
                    if cls.fail_fast:
                        raise

    @classmethod
    def parseStatement(cls, stmt_ofx):
        '''
        Parse a statement in ofx-land and return a Statement object.
        '''
        statement = Statement()
        dtstart_tag = stmt_ofx.find('dtstart')
        if hasattr(dtstart_tag, "contents"):
            try:
                statement.start_date = cls.parseOfxDateTime(
                    dtstart_tag.contents[0].strip())
            except IndexError:
                statement.warnings.append(
                    six.u("Statement start date was empty for %s") % stmt_ofx)
                if cls.fail_fast:
                    raise
            except ValueError:
                statement.warnings.append(
                    six.u("Statement start date was not allowed for \
                        %s") % stmt_ofx)
                if cls.fail_fast:
                    raise

        dtend_tag = stmt_ofx.find('dtend')
        if hasattr(dtend_tag, "contents"):
            try:
                statement.end_date = cls.parseOfxDateTime(
                    dtend_tag.contents[0].strip())
            except IndexError:
                statement.warnings.append(
                    six.u("Statement start date was empty for %s") % stmt_ofx)
                if cls.fail_fast:
                    raise
            except ValueError:
                msg = six.u("Statement start date was not formatted "
                            "correctly for %s")
                statement.warnings.append(msg % stmt_ofx)
                if cls.fail_fast:
                    raise
            except TypeError:
                statement.warnings.append(
                    six.u("Statement start date was not allowed for \
                        %s") % stmt_ofx)
                if cls.fail_fast:
                    raise

        currency_tag = stmt_ofx.find('curdef')
        if hasattr(currency_tag, "contents"):
            try:
                statement.currency = currency_tag.contents[0].strip().lower()
            except IndexError:
                statement.warnings.append(
                    six.u("Currency definition was empty for %s") % stmt_ofx)
                if cls.fail_fast:
                    raise

        cls.parseBalance(statement, stmt_ofx, 'ledgerbal',
                         'balance', 'balance_date', 'ledger')

        cls.parseBalance(statement, stmt_ofx, 'availbal', 'available_balance',
                         'available_balance_date', 'ledger')

        for transaction_ofx in stmt_ofx.findAll('stmttrn'):
            try:
                statement.transactions.append(
                    cls.parseTransaction(transaction_ofx))
            except OfxParserException:
                ofxError = sys.exc_info()[1]
                statement.discarded_entries.append(
                    {'error': str(ofxError), 'content': transaction_ofx})
                if cls.fail_fast:
                    raise

        return statement

    @classmethod
    def parseTransaction(cls, txn_ofx):
        '''
        Parse a transaction in ofx-land and return a Transaction object.
        '''
        transaction = Transaction()

        type_tag = txn_ofx.find('trntype')
        if hasattr(type_tag, 'contents'):
            try:
                transaction.type = type_tag.contents[0].lower().strip()
            except IndexError:
                raise OfxParserException(six.u("Empty transaction type"))
            except TypeError:
                raise OfxParserException(
                    six.u("No Transaction type (a required field)"))

        name_tag = txn_ofx.find('name')
        if hasattr(name_tag, "contents"):
            try:
                transaction.payee = name_tag.contents[0].strip()
            except IndexError:
                raise OfxParserException(six.u("Empty transaction name"))
            except TypeError:
                raise OfxParserException(
                    six.u("No Transaction name (a required field)"))

        memo_tag = txn_ofx.find('memo')
        if hasattr(memo_tag, "contents"):
            try:
                transaction.memo = memo_tag.contents[0].strip()
            except IndexError:
                # Memo can be empty.
                pass
            except TypeError:
                pass

        amt_tag = txn_ofx.find('trnamt')
        if hasattr(amt_tag, "contents"):
            try:
                transaction.amount = cls.toDecimal(amt_tag)
            except IndexError:
                raise OfxParserException("Invalid Transaction Date")
            except decimal.InvalidOperation:
                # Some banks use a null transaction for including interest
                # rate changes on your statement.
                if amt_tag.contents[0].strip() in ('null', '-null'):
                    transaction.amount = 0
                else:
                    raise OfxParserException(
                        six.u("Invalid Transaction Amount: '%s'") % amt_tag.contents[0])
            except TypeError:
                raise OfxParserException(
                    six.u("No Transaction Amount (a required field)"))
        else:
            raise OfxParserException(
                six.u("Missing Transaction Amount (a required field)"))

        date_tag = txn_ofx.find('dtposted')
        if hasattr(date_tag, "contents"):
            try:
                transaction.date = cls.parseOfxDateTime(
                    date_tag.contents[0].strip())
            except IndexError:
                raise OfxParserException("Invalid Transaction Date")
            except ValueError:
                ve = sys.exc_info()[1]
                raise OfxParserException(str(ve))
            except TypeError:
                raise OfxParserException(
                    six.u("No Transaction Date (a required field)"))
        else:
            raise OfxParserException(
                six.u("Missing Transaction Date (a required field)"))

        user_date_tag = txn_ofx.find('dtuser')
        if hasattr(user_date_tag, "contents"):
            try:
                transaction.user_date = cls.parseOfxDateTime(
                    user_date_tag.contents[0].strip())
            except IndexError:
                raise OfxParserException("Invalid Transaction User Date")
            except ValueError:
                ve = sys.exc_info()[1]
                raise OfxParserException(str(ve))
            except TypeError:
                pass

        id_tag = txn_ofx.find('fitid')
        if hasattr(id_tag, "contents"):
            try:
                transaction.id = id_tag.contents[0].strip()
            except IndexError:
                raise OfxParserException(six.u("Empty FIT id (a required \
                    field)"))
            except TypeError:
                raise OfxParserException(six.u("No FIT id (a required field)"))
        else:
            raise OfxParserException(six.u("Missing FIT id (a required \
                                     field)"))

        sic_tag = txn_ofx.find('sic')
        if hasattr(sic_tag, 'contents'):
            try:
                transaction.sic = sic_tag.contents[0].strip()
            except IndexError:
                raise OfxParserException(six.u("Empty transaction Standard \
                                         Industry Code (SIC)"))

        if transaction.sic is not None and transaction.sic in mcc.codes:
            try:
                transaction.mcc = mcc.codes.get(transaction.sic, '').get('combined \
                    description')
            except IndexError:
                raise OfxParserException(six.u("Empty transaction Merchant Category \
                    Code (MCC)"))
            except AttributeError:
                if cls.fail_fast:
                    raise

        checknum_tag = txn_ofx.find('checknum')
        if hasattr(checknum_tag, 'contents'):
            try:
                transaction.checknum = checknum_tag.contents[0].strip()
            except IndexError:
                raise OfxParserException(six.u("Empty Check (or other reference) \
                    number"))

        return transaction

    @classmethod
    def toDecimal(cls, tag):
        d = tag.contents[0].strip()
        # Handle 10,000.50 formatted numbers
        if re.search(r'.*\..*,', d):
            d = d.replace('.', '')
        # Handle 10.000,50 formatted numbers
        if re.search(r'.*,.*\.', d):
            d = d.replace(',', '')
        # Handle 10000,50 formatted numbers
        if '.' not in d and ',' in d:
            d = d.replace(',', '.')
        # Handle 1 025,53 formatted numbers
        d = d.replace(' ', '')
        # Handle +1058,53 formatted numbers
        d = d.replace('+', '')
        return decimal.Decimal(d)
