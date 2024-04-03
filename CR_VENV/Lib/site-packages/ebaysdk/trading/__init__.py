# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os

from ebaysdk import log
from ebaysdk.connection import BaseConnection
from ebaysdk.config import Config
from ebaysdk.utils import getNodeText, dict2xml, smart_encode
from ebaysdk.exception import RequestPaginationError, PaginationLimit


class Connection(BaseConnection):
    """Trading API class

    API documentation:
    https://www.x.com/developers/ebay/products/trading-api

    Supported calls:
    AddItem
    ReviseItem
    GetUser
    (all others, see API docs)

    Doctests:
    >>> import datetime
    >>> t = Connection(config_file=os.environ.get('EBAY_YAML'))
    >>> response = t.execute(u'GetCharities', {'CharityID': 3897})
    >>> charity_name = ''
    >>> if len( t.response.dom().xpath('//Name') ) > 0:
    ...   charity_name = t.response.dom().xpath('//Name')[0].text
    >>> print(charity_name)
    Sunshine Kids Foundation
    >>> isinstance(response.reply.Timestamp, datetime.datetime)
    True
    >>> print(t.error())
    None
    >>> t2 = Connection(errors=False, debug=False, config_file=os.environ.get('EBAY_YAML'))
    >>> response = t2.execute(u'VerifyAddItem', {})
    >>> print(t2.response_codes())
    [10009]

    Proof that utf8 errors work (calling .error() was triggering UTF8 Errors
    >>> t3 = Connection(token="WRONG_TOKEN", errors=False, debug=False, config_file=os.environ.get('EBAY_YAML'))
    >>> response = t3.execute(u'VerifyAddItem', {u'ErrorLanguage': u'de_DE'})
    >>> error = t3.error()
    >>> error.startswith('VerifyAddItem: Class: RequestError, Severity:')
    True
    """

    def __init__(self, **kwargs):
        """Trading class constructor.

        Keyword arguments:
        domain        -- API endpoint (default: api.ebay.com)
        config_file   -- YAML defaults (default: ebay.yaml)
        debug         -- debugging enabled (default: False)
        warnings      -- warnings enabled (default: False)
        uri           -- API endpoint uri (default: /ws/api.dll)
        appid         -- eBay application id
        devid         -- eBay developer id
        certid        -- eBay cert id
        token         -- eBay application/user token
        siteid        -- eBay country site id (default: 0 (US))
        compatibility -- version number (default: 648)
        https         -- execute of https (default: True)
        proxy_host    -- proxy hostname
        proxy_port    -- proxy port number
        timeout       -- HTTP request timeout (default: 20)
        parallel      -- ebaysdk parallel object
        response_encoding -- API encoding (default: XML)
        request_encoding  -- API encoding (default: XML)
        """
        super(Connection, self).__init__(method='POST', **kwargs)

        self.config = Config(domain=kwargs.get('domain', 'api.ebay.com'),
                             connection_kwargs=kwargs,
                             config_file=kwargs.get('config_file', 'ebay.yaml'))

        # override yaml defaults with args sent to the constructor
        self.config.set('domain', kwargs.get('domain', 'api.ebay.com'))
        self.config.set('uri', '/ws/api.dll')
        self.config.set('warnings', True)
        self.config.set('errors', True)
        self.config.set('https', True)
        self.config.set('siteid', '0')
        self.config.set('response_encoding', 'XML')
        self.config.set('request_encoding', 'XML')
        self.config.set('proxy_host', None)
        self.config.set('proxy_port', None)
        self.config.set('token', None)
        self.config.set('iaf_token', None)
        self.config.set('appid', None)
        self.config.set('devid', None)
        self.config.set('certid', None)
        self.config.set('compatibility', '837')
        self.config.set(
            'doc_url', 'http://developer.ebay.com/devzone/xml/docs/reference/ebay/index.html')

        self.datetime_nodes = [
            'shippingtime',
            'starttime',
            'endtime',
            'scheduletime',
            'createdtime',
            'hardexpirationtime',
            'invoicedate',
            'begindate',
            'enddate',
            'startcreationtime',
            'endcreationtime',
            'endtimefrom',
            'endtimeto',
            'updatetime',
            'lastupdatetime',
            'lastmodifiedtime',
            'modtimefrom',
            'modtimeto',
            'createtimefrom',
            'createtimeto',
            'starttimefrom',
            'starttimeto',
            'timeto',
            'paymenttimefrom',
            'paymenttimeto',
            'inventorycountlastcalculateddate',
            'registrationdate',
            'timefrom',
            'timestamp',
            'messagecreationtime',
            'resolutiontime',
            'date',
            'bankmodifydate',
            'creditcardexpiration',
            'creditcardmodifydate',
            'lastpaymentdate',
            'submittedtime',
            'announcementstarttime',
            'eventtime',
            'periodicstartdate',
            'modtime',
            'expirationtime',
            'creationtime',
            'lastusedtime',
            'disputecreatedtime',
            'disputemodifiedtime',
            'externaltransactiontime',
            'commenttime',
            'lastbidtime',
            'time',
            'creationdate',
            'lastmodifieddate',
            'receivedate',
            'expirationdate',
            'resolutiondate',
            'lastreaddate',
            'userforwarddate',
            'itemendtime',
            'userresponsedate',
            'nextretrytime',
            'deliverytime',
            'timebid',
            'paidtime',
            'shippedtime',
            'expectedreleasedate',
            'paymenttime',
            'promotionalsalestarttime',
            'promotionalsaleendtime',
            'refundtime',
            'refundrequestedtime',
            'refundcompletiontime',
            'estimatedrefundcompletiontime',
            'lastemailsenttime',
            'sellerinvoicetime',
            'estimateddeliverydate',
            'printedtime',
            'deliverydate',
            'refundgrantedtime',
            'scheduleddeliverytimemin',
            'scheduleddeliverytimemax',
            'actualdeliverytime',
            'usebydate',
            'lastopenedtime',
            'returndate',
            'revocationtime',
            'lasttimemodified',
            'createddate',
            'invoicesenttime',
            'acceptedtime',
            'sellerebaypaymentprocessenabletime',
            'useridlastchanged',
            'actionrequiredby',
        ]

        self.base_list_nodes = [
            'getmymessagesresponse.abstractrequest.detaillevel',
            'getaccountresponse.abstractrequest.outputselector',
            'getadformatleadsresponse.abstractrequest.outputselector',
            'getallbiddersresponse.abstractrequest.outputselector',
            'getbestoffersresponse.abstractrequest.outputselector',
            'getbidderlistresponse.abstractrequest.outputselector',
            'getcategoriesresponse.abstractrequest.outputselector',
            'getcategoryfeaturesresponse.abstractrequest.outputselector',
            'getcategorylistingsresponse.abstractrequest.outputselector',
            'getcrosspromotionsresponse.abstractrequest.outputselector',
            'getfeedbackresponse.abstractrequest.outputselector',
            'gethighbiddersresponse.abstractrequest.outputselector',
            'getitemresponse.abstractrequest.outputselector',
            'getitemsawaitingfeedbackresponse.abstractrequest.outputselector',
            'getitemshippingresponse.abstractrequest.outputselector',
            'getitemtransactionsresponse.abstractrequest.outputselector',
            'getmembermessagesresponse.abstractrequest.outputselector',
            'getmyebaybuyingresponse.abstractrequest.outputselector',
            'getmyebaysellingresponse.abstractrequest.outputselector',
            'getmymessagesresponse.abstractrequest.outputselector',
            'getnotificationpreferencesresponse.abstractrequest.outputselector',
            'getordersresponse.abstractrequest.outputselector',
            'getordertransactionsresponse.abstractrequest.outputselector',
            'getproductsresponse.abstractrequest.outputselector',
            'getsearchresultsresponse.abstractrequest.outputselector',
            'getsellereventsresponse.abstractrequest.outputselector',
            'getsellerlistresponse.abstractrequest.outputselector',
            'getsellerpaymentsresponse.abstractrequest.outputselector',
            'getsellertransactionsresponse.abstractrequest.outputselector',
            'getmessagepreferencesresponse.asqpreferences.subject',
            'getaccountresponse.accountentries.accountentry',
            'getaccountresponse.accountsummary.additionalaccount',
            'additemresponse.additemresponsecontainer.discountreason',
            'additemsresponse.additemresponsecontainer.discountreason',
            'setnotificationpreferencesresponse.applicationdeliverypreferences.deliveryurldetails',
            'additemresponse.attributearray.attribute',
            'additemsresponse.attributearray.attribute',
            'verifyadditemresponse.attributearray.attribute',
            'additemresponse.attribute.value',
            'additemsresponse.attribute.value',
            'addsellingmanagertemplateresponse.attribute.value',
            'addliveauctionitemresponse.attribute.value',
            'getitemrecommendationsresponse.attribute.value',
            'verifyadditemresponse.attribute.value',
            'addfixedpriceitemresponse.attribute.value',
            'relistfixedpriceitemresponse.attribute.value',
            'revisefixedpriceitemresponse.attribute.value',
            'getfeedbackresponse.averageratingdetailarray.averageratingdetails',
            'getfeedbackresponse.averageratingsummary.averageratingdetails',
            'respondtobestofferresponse.bestofferarray.bestoffer',
            'getliveauctionbiddersresponse.bidderdetailarray.bidderdetail',
            'getallbiddersresponse.biddingsummary.itembiddetails',
            'getsellerdashboardresponse.buyersatisfactiondashboard.alert',
            'getshippingdiscountprofilesresponse.calculatedshippingdiscount.discountprofile',
            'getcategoriesresponse.categoryarray.category',
            'getcategoryfeaturesresponse.categoryfeature.listingduration',
            'getcategoryfeaturesresponse.categoryfeature.paymentmethod',
            'getcategoriesresponse.category.categoryparentid',
            'getsuggestedcategoriesresponse.category.categoryparentname',
            'getcategory2csresponse.category.productfinderids',
            'getcategory2csresponse.category.characteristicssets',
            'getproductfamilymembersresponse.characteristicsset.characteristics',
            'getproductsearchpageresponse.characteristicsset.characteristics',
            'getproductsearchresultsresponse.characteristicsset.characteristics',
            'getuserresponse.charityaffiliationdetails.charityaffiliationdetail',
            'getbidderlistresponse.charityaffiliations.charityid',
            'setcharitiesresponse.charityinfo.nonprofitaddress',
            'setcharitiesresponse.charityinfo.nonprofitsocialaddress',
            'getcategoryfeaturesresponse.conditionvalues.condition',
            'getbidderlistresponse.crosspromotions.promoteditem',
            'getuserdisputesresponse.disputearray.dispute',
            'getuserdisputesresponse.dispute.disputeresolution',
            'getdisputeresponse.dispute.disputemessage',
            'setsellingmanagerfeedbackoptionsresponse.feedbackcommentarray.storedcommenttext',
            'getfeedbackresponse.feedbackdetailarray.feedbackdetail',
            'getfeedbackresponse.feedbackperiodarray.feedbackperiod',
            'addfixedpriceitemresponse.fees.fee',
            'additemresponse.fees.fee',
            'additemsresponse.fees.fee',
            'addliveauctionitemresponse.fees.fee',
            'relistfixedpriceitemresponse.fees.fee',
            'relistitemresponse.fees.fee',
            'revisefixedpriceitemresponse.fees.fee',
            'reviseitemresponse.fees.fee',
            'reviseliveauctionitemresponse.fees.fee',
            'verifyaddfixedpriceitemresponse.fees.fee',
            'verifyadditemresponse.fees.fee',
            'reviseinventorystatusresponse.fees.fee',
            'verifyrelistitemresponse.fees.fee',
            'getshippingdiscountprofilesresponse.flatshippingdiscount.discountprofile',
            'getitemrecommendationsresponse.getrecommendationsrequestcontainer.recommendationengine',
            'getitemrecommendationsresponse.getrecommendationsrequestcontainer.deletedfield',
            'getuserresponse.integratedmerchantcreditcardinfo.supportedsite',
            'sendinvoiceresponse.internationalshippingserviceoptions.shiptolocation',
            'reviseinventorystatusresponse.inventoryfees.fee',
            'getbidderlistresponse.itemarray.item',
            'getbestoffersresponse.itembestoffersarray.itembestoffers',
            'addfixedpriceitemresponse.itemcompatibilitylist.compatibility',
            'additemresponse.itemcompatibilitylist.compatibility',
            'additemfromsellingmanagertemplateresponse.itemcompatibilitylist.compatibility',
            'additemsresponse.itemcompatibilitylist.compatibility',
            'addsellingmanagertemplateresponse.itemcompatibilitylist.compatibility',
            'relistfixedpriceitemresponse.itemcompatibilitylist.compatibility',
            'relistitemresponse.itemcompatibilitylist.compatibility',
            'revisefixedpriceitemresponse.itemcompatibilitylist.compatibility',
            'reviseitemresponse.itemcompatibilitylist.compatibility',
            'revisesellingmanagertemplateresponse.itemcompatibilitylist.compatibility',
            'verifyaddfixedpriceitemresponse.itemcompatibilitylist.compatibility',
            'verifyadditemresponse.itemcompatibilitylist.compatibility',
            'verifyrelistitemresponse.itemcompatibilitylist.compatibility',
            'addfixedpriceitemresponse.itemcompatibility.namevaluelist',
            'additemresponse.itemcompatibility.namevaluelist',
            'additemfromsellingmanagertemplateresponse.itemcompatibility.namevaluelist',
            'additemsresponse.itemcompatibility.namevaluelist',
            'addsellingmanagertemplateresponse.itemcompatibility.namevaluelist',
            'relistfixedpriceitemresponse.itemcompatibility.namevaluelist',
            'relistitemresponse.itemcompatibility.namevaluelist',
            'revisefixedpriceitemresponse.itemcompatibility.namevaluelist',
            'reviseitemresponse.itemcompatibility.namevaluelist',
            'revisesellingmanagertemplateresponse.itemcompatibility.namevaluelist',
            'verifyadditemresponse.itemcompatibility.namevaluelist',
            'verifyrelistitemresponse.itemcompatibility.namevaluelist',
            'getpromotionalsaledetailsresponse.itemidarray.itemid',
            'leavefeedbackresponse.itemratingdetailarray.itemratingdetails',
            'getordertransactionsresponse.itemtransactionidarray.itemtransactionid',
            'addfixedpriceitemresponse.item.giftservices',
            'additemresponse.item.giftservices',
            'additemsresponse.item.giftservices',
            'addsellingmanagertemplateresponse.item.giftservices',
            'getitemrecommendationsresponse.item.giftservices',
            'relistfixedpriceitemresponse.item.giftservices',
            'relistitemresponse.item.giftservices',
            'revisefixedpriceitemresponse.item.giftservices',
            'reviseitemresponse.item.giftservices',
            'revisesellingmanagertemplateresponse.item.giftservices',
            'verifyadditemresponse.item.giftservices',
            'verifyrelistitemresponse.item.giftservices',
            'addfixedpriceitemresponse.item.listingenhancement',
            'additemresponse.item.listingenhancement',
            'additemsresponse.item.listingenhancement',
            'addsellingmanagertemplateresponse.item.listingenhancement',
            'getitemrecommendationsresponse.item.listingenhancement',
            'relistfixedpriceitemresponse.item.listingenhancement',
            'relistitemresponse.item.listingenhancement',
            'revisefixedpriceitemresponse.item.listingenhancement',
            'reviseitemresponse.item.listingenhancement',
            'revisesellingmanagertemplateresponse.item.listingenhancement',
            'verifyadditemresponse.item.listingenhancement',
            'verifyrelistitemresponse.item.listingenhancement',
            'addfixedpriceitemresponse.item.paymentmethods',
            'additemresponse.item.paymentmethods',
            'additemfromsellingmanagertemplateresponse.item.paymentmethods',
            'additemsresponse.item.paymentmethods',
            'addsellingmanagertemplateresponse.item.paymentmethods',
            'relistfixedpriceitemresponse.item.paymentmethods',
            'relistitemresponse.item.paymentmethods',
            'revisefixedpriceitemresponse.item.paymentmethods',
            'reviseitemresponse.item.paymentmethods',
            'verifyadditemresponse.item.paymentmethods',
            'verifyrelistitemresponse.item.paymentmethods',
            'addfixedpriceitemresponse.item.shiptolocations',
            'additemresponse.item.shiptolocations',
            'additemsresponse.item.shiptolocations',
            'addsellingmanagertemplateresponse.item.shiptolocations',
            'getitemrecommendationsresponse.item.shiptolocations',
            'relistfixedpriceitemresponse.item.shiptolocations',
            'relistitemresponse.item.shiptolocations',
            'revisefixedpriceitemresponse.item.shiptolocations',
            'reviseitemresponse.item.shiptolocations',
            'revisesellingmanagertemplateresponse.item.shiptolocations',
            'verifyadditemresponse.item.shiptolocations',
            'verifyrelistitemresponse.item.shiptolocations',
            'addfixedpriceitemresponse.item.skypecontactoption',
            'additemresponse.item.skypecontactoption',
            'additemsresponse.item.skypecontactoption',
            'addsellingmanagertemplateresponse.item.skypecontactoption',
            'relistfixedpriceitemresponse.item.skypecontactoption',
            'relistitemresponse.item.skypecontactoption',
            'revisefixedpriceitemresponse.item.skypecontactoption',
            'reviseitemresponse.item.skypecontactoption',
            'revisesellingmanagertemplateresponse.item.skypecontactoption',
            'verifyadditemresponse.item.skypecontactoption',
            'verifyrelistitemresponse.item.skypecontactoption',
            'addfixedpriceitemresponse.item.crossbordertrade',
            'additemresponse.item.crossbordertrade',
            'additemsresponse.item.crossbordertrade',
            'addsellingmanagertemplateresponse.item.crossbordertrade',
            'relistfixedpriceitemresponse.item.crossbordertrade',
            'relistitemresponse.item.crossbordertrade',
            'revisefixedpriceitemresponse.item.crossbordertrade',
            'reviseitemresponse.item.crossbordertrade',
            'revisesellingmanagertemplateresponse.item.crossbordertrade',
            'verifyadditemresponse.item.crossbordertrade',
            'verifyrelistitemresponse.item.crossbordertrade',
            'getitemresponse.item.paymentallowedsite',
            'getsellingmanagertemplatesresponse.item.paymentallowedsite',
            'getcategoryfeaturesresponse.listingdurationdefinition.duration',
            'getcategoryfeaturesresponse.listingdurationdefinitions.listingduration',
            'getcategoryfeaturesresponse.listingenhancementdurationreference.duration',
            'addfixedpriceitemresponse.listingrecommendation.value',
            'additemresponse.listingrecommendation.value',
            'additemsresponse.listingrecommendation.value',
            'relistfixedpriceitemresponse.listingrecommendation.value',
            'relistitemresponse.listingrecommendation.value',
            'revisefixedpriceitemresponse.listingrecommendation.value',
            'reviseitemresponse.listingrecommendation.value',
            'verifyadditemresponse.listingrecommendation.value',
            'verifyaddfixedpriceitemresponse.listingrecommendation.value',
            'verifyrelistitemresponse.listingrecommendation.value',
            'addfixedpriceitemresponse.listingrecommendations.recommendation',
            'additemresponse.listingrecommendations.recommendation',
            'additemsresponse.listingrecommendations.recommendation',
            'relistfixedpriceitemresponse.listingrecommendations.recommendation',
            'relistitemresponse.listingrecommendations.recommendation',
            'revisefixedpriceitemresponse.listingrecommendations.recommendation',
            'reviseitemresponse.listingrecommendations.recommendation',
            'verifyadditemresponse.listingrecommendations.recommendation',
            'verifyaddfixedpriceitemresponse.listingrecommendations.recommendation',
            'verifyrelistitemresponse.listingrecommendations.recommendation',
            'getitemrecommendationsresponse.listingtiparray.listingtip',
            'getnotificationsusageresponse.markupmarkdownhistory.markupmarkdownevent',
            'getebaydetailsresponse.maximumbuyerpolicyviolationsdetails.policyviolationduration',
            'getebaydetailsresponse.maximumitemrequirementsdetails.maximumitemcount',
            'getebaydetailsresponse.maximumitemrequirementsdetails.minimumfeedbackscore',
            'getebaydetailsresponse.maximumunpaiditemstrikescountdetails.count',
            'getebaydetailsresponse.maximumunpaiditemstrikesinfodetails.maximumunpaiditemstrikesduration',
            'getadformatleadsresponse.membermessageexchangearray.membermessageexchange',
            'getadformatleadsresponse.membermessageexchange.response',
            'getmembermessagesresponse.membermessageexchange.messagemedia',
            'addmembermessageaaqtopartnerresponse.membermessage.recipientid',
            'addmembermessagertqresponse.membermessage.recipientid',
            'addmembermessagesaaqtobidderresponse.membermessage.recipientid',
            'addmembermessageaaqtopartnerresponse.membermessage.messagemedia',
            'addmembermessagertqresponse.membermessage.messagemedia',
            'addmembermessagecemresponse.membermessage.messagemedia',
            'addmembermessageaaqtosellerresponse.membermessage.messagemedia',
            'getebaydetailsresponse.minimumfeedbackscoredetails.feedbackscore',
            'relistfixedpriceitemresponse.modifynamearray.modifyname',
            'revisefixedpriceitemresponse.modifynamearray.modifyname',
            'getmymessagesresponse.mymessagesexternalmessageidarray.externalmessageid',
            'getmymessagesresponse.mymessagesmessagearray.message',
            'deletemymessagesresponse.mymessagesmessageidarray.messageid',
            'getmymessagesresponse.mymessagesmessage.messagemedia',
            'getmymessagesresponse.mymessagessummary.foldersummary',
            'getmyebaybuyingresponse.myebayfavoritesearchlist.favoritesearch',
            'getmyebaybuyingresponse.myebayfavoritesearch.searchflag',
            'getmyebaybuyingresponse.myebayfavoritesearch.sellerid',
            'getmyebaybuyingresponse.myebayfavoritesearch.selleridexclude',
            'getmyebaybuyingresponse.myebayfavoritesellerlist.favoriteseller',
            'getcategoryspecificsresponse.namerecommendation.valuerecommendation',
            'getitemrecommendationsresponse.namerecommendation.valuerecommendation',
            'addfixedpriceitemresponse.namevaluelistarray.namevaluelist',
            'additemresponse.namevaluelistarray.namevaluelist',
            'additemsresponse.namevaluelistarray.namevaluelist',
            'addsellingmanagertemplateresponse.namevaluelistarray.namevaluelist',
            'addliveauctionitemresponse.namevaluelistarray.namevaluelist',
            'relistfixedpriceitemresponse.namevaluelistarray.namevaluelist',
            'relistitemresponse.namevaluelistarray.namevaluelist',
            'revisefixedpriceitemresponse.namevaluelistarray.namevaluelist',
            'reviseitemresponse.namevaluelistarray.namevaluelist',
            'revisesellingmanagertemplateresponse.namevaluelistarray.namevaluelist',
            'reviseliveauctionitemresponse.namevaluelistarray.namevaluelist',
            'verifyaddfixedpriceitemresponse.namevaluelistarray.namevaluelist',
            'verifyadditemresponse.namevaluelistarray.namevaluelist',
            'verifyrelistitemresponse.namevaluelistarray.namevaluelist',
            'additemresponse.namevaluelist.value',
            'additemfromsellingmanagertemplateresponse.namevaluelist.value',
            'additemsresponse.namevaluelist.value',
            'addsellingmanagertemplateresponse.namevaluelist.value',
            'addliveauctionitemresponse.namevaluelist.value',
            'relistitemresponse.namevaluelist.value',
            'reviseitemresponse.namevaluelist.value',
            'revisesellingmanagertemplateresponse.namevaluelist.value',
            'reviseliveauctionitemresponse.namevaluelist.value',
            'verifyadditemresponse.namevaluelist.value',
            'verifyrelistitemresponse.namevaluelist.value',
            'getnotificationsusageresponse.notificationdetailsarray.notificationdetails',
            'setnotificationpreferencesresponse.notificationenablearray.notificationenable',
            'setnotificationpreferencesresponse.notificationuserdata.summaryschedule',
            'getebaydetailsresponse.numberofpolicyviolationsdetails.count',
            'getallbiddersresponse.offerarray.offer',
            'gethighbiddersresponse.offerarray.offer',
            'getordersresponse.orderarray.order',
            'getordersresponse.orderarray.order.transactionarray.transaction',
            'getordersresponse.orderidarray.orderid',
            'getmyebaybuyingresponse.ordertransactionarray.ordertransaction',
            'addorderresponse.order.paymentmethods',
            'getordertransactionsresponse.order.externaltransaction',
            'getordersresponse.order.externaltransaction',
            'getordersresponse.paymentinformationcode.payment',
            'getordersresponse.paymentinformation.payment',
            'getordersresponse.paymenttransactioncode.paymentreferenceid',
            'getordersresponse.paymenttransaction.paymentreferenceid',
            'getsellerdashboardresponse.performancedashboard.site',
            'getordersresponse.pickupdetails.pickupoptions',
            'additemresponse.picturedetails.pictureurl',
            'additemsresponse.picturedetails.pictureurl',
            'addsellingmanagertemplateresponse.picturedetails.pictureurl',
            'getitemrecommendationsresponse.picturedetails.pictureurl',
            'relistitemresponse.picturedetails.pictureurl',
            'reviseitemresponse.picturedetails.pictureurl',
            'revisesellingmanagertemplateresponse.picturedetails.pictureurl',
            'verifyadditemresponse.picturedetails.pictureurl',
            'verifyrelistitemresponse.picturedetails.pictureurl',
            'getitemresponse.picturedetails.externalpictureurl',
            'addfixedpriceitemresponse.pictures.variationspecificpictureset',
            'verifyaddfixedpriceitemresponse.pictures.variationspecificpictureset',
            'relistfixedpriceitemresponse.pictures.variationspecificpictureset',
            'revisefixedpriceitemresponse.pictures.variationspecificpictureset',
            'getsellerdashboardresponse.powersellerdashboard.alert',
            'getbidderlistresponse.productlistingdetails.copyright',
            'getitemrecommendationsresponse.productrecommendations.product',
            'addfixedpriceitemresponse.productsuggestions.productsuggestion',
            'additemresponse.productsuggestions.productsuggestion',
            'relistfixedpriceitemresponse.productsuggestions.productsuggestion',
            'relistitemresponse.productsuggestions.productsuggestion',
            'revisefixedpriceitemresponse.productsuggestions.productsuggestion',
            'reviseitemresponse.productsuggestions.productsuggestion',
            'verifyadditemresponse.productsuggestions.productsuggestion',
            'verifyrelistitemresponse.productsuggestions.productsuggestion',
            'getpromotionalsaledetailsresponse.promotionalsalearray.promotionalsale',
            'addfixedpriceitemresponse.recommendation.recommendedvalue',
            'additemresponse.recommendation.recommendedvalue',
            'additemsresponse.recommendation.recommendedvalue',
            'relistfixedpriceitemresponse.recommendation.recommendedvalue',
            'relistitemresponse.recommendation.recommendedvalue',
            'revisefixedpriceitemresponse.recommendation.recommendedvalue',
            'reviseitemresponse.recommendation.recommendedvalue',
            'verifyadditemresponse.recommendation.recommendedvalue',
            'verifyaddfixedpriceitemresponse.recommendation.recommendedvalue',
            'verifyrelistitemresponse.recommendation.recommendedvalue',
            'getcategoryspecificsresponse.recommendationvalidationrules.relationship',
            'getitemrecommendationsresponse.recommendationvalidationrules.relationship',
            'getcategoryspecificsresponse.recommendations.namerecommendation',
            'getitemrecommendationsresponse.recommendations.namerecommendation',
            'getuserresponse.recoupmentpolicyconsent.site',
            'getordersresponse.refundarray.refund',
            'getordersresponse.refundfundingsourcearray.refundfundingsource',
            'getitemtransactionsresponse.refundfundingsourcearray.refundfundingsource',
            'getordertransactionsresponse.refundfundingsourcearray.refundfundingsource',
            'getsellertransactionsresponse.refundfundingsourcearray.refundfundingsource',
            'getordersresponse.refundinformation.refund',
            'getordersresponse.refundlinearray.refundline',
            'getitemtransactionsresponse.refundlinearray.refundline',
            'getordertransactionsresponse.refundlinearray.refundline',
            'getsellertransactionsresponse.refundlinearray.refundline',
            'getordersresponse.refundtransactionarray.refundtransaction',
            'getitemtransactionsresponse.refundtransactionarray.refundtransaction',
            'getordertransactionsresponse.refundtransactionarray.refundtransaction',
            'getsellertransactionsresponse.refundtransactionarray.refundtransaction',
            'getordersresponse.requiredselleractionarray.requiredselleraction',
            'getebaydetailsresponse.returnpolicydetails.refund',
            'getebaydetailsresponse.returnpolicydetails.returnswithin',
            'getebaydetailsresponse.returnpolicydetails.returnsaccepted',
            'getebaydetailsresponse.returnpolicydetails.warrantyoffered',
            'getebaydetailsresponse.returnpolicydetails.warrantytype',
            'getebaydetailsresponse.returnpolicydetails.warrantyduration',
            'getebaydetailsresponse.returnpolicydetails.shippingcostpaidby',
            'getebaydetailsresponse.returnpolicydetails.restockingfeevalue',
            'getsellertransactionsresponse.skuarray.sku',
            'getsellerlistresponse.skuarray.sku',
            'getsellerdashboardresponse.selleraccountdashboard.alert',
            'getitemtransactionsresponse.sellerdiscounts.sellerdiscount',
            'getordersresponse.sellerdiscounts.sellerdiscount',
            'getordertransactionsresponse.sellerdiscounts.sellerdiscount',
            'getsellertransactionsresponse.sellerdiscounts.sellerdiscount',
            'getuserpreferencesresponse.sellerexcludeshiptolocationpreferences.excludeshiptolocation',
            'getuserpreferencesresponse.sellerfavoriteitempreferences.favoriteitemid',
            'getfeedbackresponse.sellerratingsummaryarray.averageratingsummary',
            'getbidderlistresponse.sellerebaypaymentprocessconsentcode.useragreementinfo',
            'getsellingmanagertemplateautomationruleresponse.sellingmanagerautolistaccordingtoschedule.dayofweek',
            'getsellingmanagerinventoryfolderresponse.sellingmanagerfolderdetails.childfolder',
            'revisesellingmanagerinventoryfolderresponse.sellingmanagerfolderdetails.childfolder',
            'getsellingmanagersalerecordresponse.sellingmanagersoldorder.sellingmanagersoldtransaction',
            'getsellingmanagersoldlistingsresponse.sellingmanagersoldorder.sellingmanagersoldtransaction',
            'getsellingmanagersalerecordresponse.sellingmanagersoldorder.vatrate',
            'getsellingmanagersoldlistingsresponse.sellingmanagersoldtransaction.listedon',
            'getsellingmanagertemplatesresponse.sellingmanagertemplatedetailsarray.sellingmanagertemplatedetails',
            'completesaleresponse.shipmentlineitem.lineitem',
            'addshipmentresponse.shipmentlineitem.lineitem',
            'reviseshipmentresponse.shipmentlineitem.lineitem',
            'revisesellingmanagersalerecordresponse.shipmentlineitem.lineitem',
            'setshipmenttrackinginforesponse.shipmentlineitem.lineitem',
            'completesaleresponse.shipment.shipmenttrackingdetails',
            'getitemresponse.shippingdetails.shippingserviceoptions',
            'getsellingmanagertemplatesresponse.shippingdetails.shippingserviceoptions',
            'addfixedpriceitemresponse.shippingdetails.internationalshippingserviceoption',
            'additemresponse.shippingdetails.internationalshippingserviceoption',
            'additemsresponse.shippingdetails.internationalshippingserviceoption',
            'addsellingmanagertemplateresponse.shippingdetails.internationalshippingserviceoption',
            'addorderresponse.shippingdetails.internationalshippingserviceoption',
            'getitemrecommendationsresponse.shippingdetails.internationalshippingserviceoption',
            'relistfixedpriceitemresponse.shippingdetails.internationalshippingserviceoption',
            'relistitemresponse.shippingdetails.internationalshippingserviceoption',
            'revisefixedpriceitemresponse.shippingdetails.internationalshippingserviceoption',
            'reviseitemresponse.shippingdetails.internationalshippingserviceoption',
            'revisesellingmanagertemplateresponse.shippingdetails.internationalshippingserviceoption',
            'verifyadditemresponse.shippingdetails.internationalshippingserviceoption',
            'verifyrelistitemresponse.shippingdetails.internationalshippingserviceoption',
            'getsellerlistresponse.shippingdetails.excludeshiptolocation',
            'getitemtransactionsresponse.shippingdetails.shipmenttrackingdetails',
            'getsellertransactionsresponse.shippingdetails.shipmenttrackingdetails',
            'getshippingdiscountprofilesresponse.shippinginsurance.flatrateinsurancerangecost',
            'addfixedpriceitemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'additemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'additemsresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'verifyadditemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'verifyaddfixedpriceitemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'verifyrelistitemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'relistfixedpriceitemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'relistitemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'revisefixedpriceitemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'reviseitemresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'addsellingmanagertemplateresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'revisesellingmanagertemplateresponse.shippingservicecostoverridelist.shippingservicecostoverride',
            'getebaydetailsresponse.shippingservicedetails.servicetype',
            'getebaydetailsresponse.shippingservicedetails.shippingpackage',
            'getebaydetailsresponse.shippingservicedetails.shippingcarrier',
            'getebaydetailsresponse.shippingservicedetails.deprecationdetails',
            'getebaydetailsresponse.shippingservicedetails.shippingservicepackagedetails',
            'getordersresponse.shippingserviceoptions.shippingpackageinfo',
            'getcategoryfeaturesresponse.sitedefaults.listingduration',
            'getcategoryfeaturesresponse.sitedefaults.paymentmethod',
            'uploadsitehostedpicturesresponse.sitehostedpicturedetails.picturesetmember',
            'getcategory2csresponse.sitewidecharacteristics.excludecategoryid',
            'getstoreoptionsresponse.storecolorschemearray.colorscheme',
            'getstoreresponse.storecustomcategoryarray.customcategory',
            'getstoreresponse.storecustomcategory.childcategory',
            'setstorecategoriesresponse.storecustomcategory.childcategory',
            'setstoreresponse.storecustomlistingheader.linktoinclude',
            'getstorecustompageresponse.storecustompagearray.custompage',
            'getstoreoptionsresponse.storelogoarray.logo',
            'getcategoryfeaturesresponse.storeownerextendedlistingdurations.duration',
            'getstoreoptionsresponse.storesubscriptionarray.subscription',
            'getstoreoptionsresponse.storethemearray.theme',
            'getsuggestedcategoriesresponse.suggestedcategoryarray.suggestedcategory',
            'getuserpreferencesresponse.supportedsellerprofiles.supportedsellerprofile',
            'settaxtableresponse.taxtable.taxjurisdiction',
            'getitemtransactionsresponse.taxes.taxdetails',
            'getordersresponse.taxes.taxdetails',
            'getordertransactionsresponse.taxes.taxdetails',
            'getsellertransactionsresponse.taxes.taxdetails',
            'getdescriptiontemplatesresponse.themegroup.themeid',
            'getuserresponse.topratedsellerdetails.topratedprogram',
            'getordersresponse.transactionarray.transaction',
            'getitemtransactionsresponse.transaction.externaltransaction',
            'getsellertransactionsresponse.transaction.externaltransaction',
            'getebaydetailsresponse.unitofmeasurementdetails.unitofmeasurement',
            'getebaydetailsresponse.unitofmeasurement.alternatetext',
            'getuserpreferencesresponse.unpaiditemassistancepreferences.excludeduser',
            'getsellerlistresponse.useridarray.userid',
            'getuserresponse.user.usersubscription',
            'getuserresponse.user.skypeid',
            'addfixedpriceitemresponse.variationspecificpictureset.pictureurl',
            'revisefixedpriceitemresponse.variationspecificpictureset.pictureurl',
            'relistfixedpriceitemresponse.variationspecificpictureset.pictureurl',
            'verifyaddfixedpriceitemresponse.variationspecificpictureset.pictureurl',
            'getitemresponse.variationspecificpictureset.externalpictureurl',
            'getitemsresponse.variationspecificpictureset.externalpictureurl',
            'addfixedpriceitemresponse.variations.variation',
            'revisefixedpriceitemresponse.variations.variation',
            'relistfixedpriceitemresponse.variations.variation',
            'verifyaddfixedpriceitemresponse.variations.variation',
            'addfixedpriceitemresponse.variations.pictures',
            'revisefixedpriceitemresponse.variations.pictures',
            'relistfixedpriceitemresponse.variations.pictures',
            'verifyaddfixedpriceitemresponse.variations.pictures',
            'getveroreasoncodedetailsresponse.veroreasoncodedetails.verositedetail',
            'veroreportitemsresponse.veroreportitem.region',
            'veroreportitemsresponse.veroreportitem.country',
            'veroreportitemsresponse.veroreportitems.reportitem',
            'getveroreportstatusresponse.veroreporteditemdetails.reporteditem',
            'getveroreasoncodedetailsresponse.verositedetail.reasoncodedetail',
            'getebaydetailsresponse.verifieduserrequirementsdetails.feedbackscore',
            'getwantitnowsearchresultsresponse.wantitnowpostarray.wantitnowpost',
        ]

    def build_request_headers(self, verb):
        headers = {
            "X-EBAY-API-COMPATIBILITY-LEVEL": self.config.get('compatibility', ''),
            "X-EBAY-API-DEV-NAME": self.config.get('devid', ''),
            "X-EBAY-API-APP-NAME": self.config.get('appid', ''),
            "X-EBAY-API-CERT-NAME": self.config.get('certid', ''),
            "X-EBAY-API-SITEID": str(self.config.get('siteid', '')),
            "X-EBAY-API-CALL-NAME": self.verb,
            "Content-Type": "text/xml"
        }
        if self.config.get('iaf_token', None):
            headers["X-EBAY-API-IAF-TOKEN"] = self.config.get('iaf_token')

        return headers

    def build_request_data(self, verb, data, verb_attrs):
        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<{verb}Request xmlns=\"urn:ebay:apis:eBLBaseComponents\">".format(
            verb=self.verb)
        if not self.config.get('iaf_token', None):
            xml += "<RequesterCredentials>"
            if self.config.get('token', None):
                xml += "<eBayAuthToken>{token}</eBayAuthToken>".format(
                    token=self.config.get('token'))
            elif self.config.get('username', None):
                xml += "<Username>{username}</Username>".format(
                    username=self.config.get('username', ''))
                if self.config.get('password', None):
                    xml += "<Password>{password}</Password>".format(
                        password=self.config.get('password', None))
            xml += "</RequesterCredentials>"
        xml += dict2xml(data, self.escape_xml)
        xml += "</{verb}Request>".format(verb=self.verb)
        return xml

    def warnings(self):
        warning_string = ""

        if len(self._resp_body_warnings) > 0:
            warning_string = "{verb}: {message}" \
                .format(verb=self.verb, message=", ".join(self._resp_body_warnings))

        return warning_string

    def _get_resp_body_errors(self):
        """Parses the response content to pull errors.

        Child classes should override this method based on what the errors in the
        XML response body look like. They can choose to look at the 'ack',
        'Errors', 'errorMessage' or whatever other fields the service returns.
        the implementation below is the original code that was part of error()
        """

        if self._resp_body_errors and len(self._resp_body_errors) > 0:
            return self._resp_body_errors

        errors = []
        warnings = []
        resp_codes = []

        if self.verb is None:
            return errors

        dom = self.response.dom()
        if dom is None:
            return errors

        for e in dom.findall('Errors'):
            eSeverity = None
            eClass = None
            eShortMsg = None
            eLongMsg = None
            eCode = None

            try:
                eSeverity = e.findall('SeverityCode')[0].text
            except IndexError:
                pass

            try:
                eClass = e.findall('ErrorClassification')[0].text
            except IndexError:
                pass

            try:
                eCode = e.findall('ErrorCode')[0].text
            except IndexError:
                pass

            try:
                eShortMsg = smart_encode(e.findall('ShortMessage')[0].text)
            except IndexError:
                pass

            try:
                eLongMsg = smart_encode(e.findall('LongMessage')[0].text)
            except IndexError:
                pass

            try:
                eCode = e.findall('ErrorCode')[0].text
                if int(eCode) not in resp_codes:
                    resp_codes.append(int(eCode))
            except IndexError:
                pass

            msg = str("Class: {eClass}, Severity: {severity}, Code: {code}, {shortMsg} {longMsg}") \
                .format(eClass=eClass, severity=eSeverity, code=eCode, shortMsg=eShortMsg,
                        longMsg=eLongMsg)

            # from IPython import embed; embed()

            if eSeverity == 'Warning':
                warnings.append(msg)
            else:
                errors.append(msg)

        self._resp_body_warnings = warnings
        self._resp_body_errors = errors
        self._resp_codes = resp_codes

        if self.config.get('warnings') and len(warnings) > 0:
            log.warn("{verb}: {message}\n\n".format(
                verb=self.verb, message="\n".join(warnings)))

        if self.response.reply.Ack == 'Failure':
            if self.config.get('errors'):
                log.error("{verb}: {message}\n\n".format(
                    verb=self.verb, message="\n".join(errors)))

            return errors

        return []

    def pages(self):

        tot_pages = 0
        epp = self._request_dict.get(
            'Pagination', {}).get('EntriesPerPage', None)

        if not self.response:
            resp = self.execute(self.verb, self._request_dict)
            tot_pages = int(resp.reply.PaginationResult.TotalNumberOfPages)
            yield resp

        for page in range(tot_pages)[1:]:
            self._request_dict['Pagination'] = {}

            if epp:
                self._request_dict['Pagination']['EntriesPerPage'] = epp

            self._request_dict['Pagination']['PageNumber'] = int(page) + 1

            yield self.execute(self.verb, self._request_dict)
