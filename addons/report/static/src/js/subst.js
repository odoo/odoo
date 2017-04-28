function subst() {
    var vars = {};
    var x = document.location.search.substring(1).split('&');
    for (var i in x) {
        var z = x[i].split('=', 2);
        vars[z[0]] = unescape(z[1]);
    }
    var x=['frompage', 'topage', 'page', 'webpage', 'section', 'subsection', 'subsubsection'];
    for (var i in x) {
        var y = document.getElementsByClassName(x[i]);
        for (var j=0; j<y.length; ++j)
            y[j].textContent = vars[x[i]];
    }

    if (vars['page'] == 1){
        hidden_nodes = document.getElementsByClassName("hide_firstpage");
        for (i = 0; i < hidden_nodes.length; i++) {
            hidden_nodes[i].style.visibility = "hidden";
        }
    }

    if (vars['page'] != vars['topage']){
        hidden_nodes = document.getElementsByClassName("show_lastpage");
        for (i = 0; i < hidden_nodes.length; i++) {
            hidden_nodes[i].style.visibility = "hidden";
        }
    }
}
