(function() {
       
    $(document).ready(function() {

        var _gaq = _gaq || [];
        _gaq.push(['_setAccount', 'UA-7333765-1']);
        _gaq.push(['_setDomainName', '.openerp.com']);

        (function() {
            var ga   = document.createElement('script');
            ga.type  = 'text/javascript';
            ga.async = true;
            ga.src   = ('https:' === document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
            var s = document.getElementsByTagName('script')[0];
            s.parentNode.insertBefore(ga,s);
        })();

        var view_id = $('html').attr('data-view-xmlid');
        //console.log(view_id);
        openerp.jsonRpc( '/website_version/get_analytics', 'call', { 'view_id':view_id }).then(function (result) {
                    //console.log(result);
                    _gaq.push(['_setCustomVar', 4, result['experiment_id'], result['snapshot_id'], 1]);
                });
    });
    
})();