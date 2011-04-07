// Automatically load dependencies, in order, if they aren't already loaded.
// Each array is: [filename, deptest] where deptest is the function to
// test for the dependency.
var AjaxIM, AjaxIMLoadedFunction;
(function() {
    AjaxIM = {};
    AjaxIM.loaded = function(f) {
        AjaxIMLoadedFunction = f;
    };

    var tagsrc =
        (thistag = document.getElementsByTagName('script'))[thistag.length-1].src;
    var jsfolder = tagsrc.replace(/im.load.js([?].+)?/, '');
    var imfolder = jsfolder.replace(/js\/$/, '');

    var nodehost = '';

    var dependencies = [
        ['jquery-1.3.2.js', function() { return (typeof window['jQuery'] != 'undefined'); }],
        ['jquery.jsonp-1.1.0.js', function() { return (typeof jQuery['jsonp'] != 'undefined'); }],
        ['jquery.jstore-all-min.js', function() { return (typeof jQuery['jstore'] != 'undefined'); }],
        ['jquery.md5.js', function() { return (typeof jQuery['md5'] != 'undefined'); }],
        ['im.js', function() { return (typeof window['AjaxIM'] != 'object'); }]
    ];
    
    var head = document.getElementsByTagName('head')[0];
    
    (loadDep = function(depPos) {        
        if(depPos >= dependencies.length) { init(); return; }
        var dep = dependencies[depPos];
        
        if(!dep[1]()) {
            var newdep = document.createElement('script');
            newdep.type = 'text/javascript';
            newdep.src = jsfolder + dep[0];

            var nextdep = function() { loadDep(depPos + 1); };
            newdep.onload = nextdep;
            newdep.onreadystatechange = nextdep;

            head.appendChild(newdep);
        } else loadDep(depPos + 1);
    })(0);
    
    var init = function() {
        if(tagsrc.match(/[?]php$/)) {
            AjaxIM.init({
                pollServer: imfolder + 'ajaxim.php',
                theme: imfolder + 'themes/default',
                flashStorage: jsfolder + 'jStore.Flash.html'
            });
        } else if(tagsrc.match(/[?]node$/)) {
            AjaxIM.init({
                pollServer: imfolder + 'ajaxim.php',
                theme: imfolder + 'themes/default',
                flashStorage: jsfolder + 'jStore.Flash.html'
            }, {
                poll: 'http://' + nodehost + '/poll',
                send: 'http://' + nodehost + '/send',
                status: 'http://' + nodehost + '/status',
                resume: 'http://' + nodehost + '/resume'
            });
        } else if(tagsrc.match(/[?]guest$/)) {
            AjaxIM.init({
                pollServer: imfolder + 'ajaxim.php',
                theme: imfolder + 'themes/default',
                flashStorage: jsfolder + 'jStore.Flash.html'
            }, {
                poll: 'http://' + nodehost + '/poll',
                send: 'http://' + nodehost + '/send',
                status: 'http://' + nodehost + '/status',
                resume: 'http://' + nodehost + '/resume'
            });
            AjaxIM.client.login();
        }
        
        AjaxIM.loaded();
    };
})();