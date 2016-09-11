$(function() {
    console.log('Salut');
    if(_.str.startsWith(window.location.hash,'#test=')) {
        options = JSON.parse(decodeURIComponent(window.location.hash.substr(6)));
        console.log('Options');
        console.log(options);
        if(options.login) {
            var qp = [];
            qp.push('db=' + options.db);
            qp.push('login=' + options.login);
            qp.push('key=' + options.password);
            // TODO re-encode JSON without login
            // qp.push('redirect=' + encodeURIComponent(url_path));
            url_path = "/login?" + qp.join('&');
            window.location = url_path;
        }
        waitForReady = function() {
            try {
                console.log("waitForRead test ready:", options.ready);
                r = !!eval(options.ready);
            } catch(ex) {
                console.log("waitForReady NOT READY");
                setTimeout(waitForReady, 250)
            }
            console.log("waitForReady condition TRUE");
            eval(options.code);
        }
        setTimeout(waitForReady)
    }
})
