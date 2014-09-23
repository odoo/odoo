(function() {
       
    $(document).ready(function() {

        (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
        (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
        m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
        })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

        ga('create', 'UA-55031254-1', 'auto');
        ga('send', 'pageview');


        var _gaq = _gaq || [];
        _gaq.push(['_setAccount', 'UA-55031254-1']);
        //_gaq.push(['_setDomainName', '.openerp.com']);
        _gaq.push(["_setDomainName", "none"]);
        _gaq.push(["_trackPageview"]);

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
                    _gaq.push(['_setCustomVar', 4, "exp_"+result['experiment_id'], result['snapshot_id'], 1]);
                    var dimensionValue = "exp_"+result['experiment_id']+"_snap_"+result['snapshot_id'];
                    ga('set', 'dimension1', dimensionValue);
                    ga('send', 'dimension1');
                    var dimensionValue3 = result['snapshot_id'];
                    ga('set', 'dimension3', dimensionValue3);
                    ga('send', 'dimension3');
                });
    });
    
})();