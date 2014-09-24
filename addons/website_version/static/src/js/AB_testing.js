(function() {
       
    $(document).ready(function() {

        // (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
        // (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
        // m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
        // })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

        // ga('create', 'UA-55031254-1', {'cookieDomain': 'none'});

        var _gaq = _gaq || [];
        _gaq.push(['_setAccount', 'UA-55031254-1']);
        _gaq.push(['_setDomainName', 'none']);
        _gaq.push(['_setAllowLinker', true]);
        _gaq.push(['_trackPageview']);

        (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
        (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
        m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
        })(window,document,'script','//www.google-analytics.com/analytics.js','_gaw');

        _gaw('create',_.str.trim('UA-55031254-1'), {'cookieDomain': 'none'});
        _gaw('send','pageview');

        var view_id = $('html').attr('data-view-xmlid');
        //console.log(view_id);
        openerp.jsonRpc( '/website_version/get_analytics', 'call', { 'view_id':view_id }).then(function (result) {
                    console.log(result);
                    _gaq.push(['_setCustomVar', 4, "exp_"+result['experiment_id'], "snap"+result['snapshot_id'], 3]);
                });
    });
    
})();