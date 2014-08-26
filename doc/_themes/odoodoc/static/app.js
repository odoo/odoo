$(function () {
    var $body = $(document.body);
    $body.scrollspy({ target: '.sphinxsidebarwrapper' });
    $(window).on('load', function () {
        $body.scrollspy('refresh');
    });

    // Sidenav affixing
    setTimeout(function () {
        var $sideBar = $('.sphinxsidebarwrapper');

        $sideBar.affix({
            offset: {
                top: function () {
                    var offsetTop = $sideBar.offset().top;
                    var sideBarMargin = parseInt($sideBar.children(0).css('margin-top'), 10);
                    var navOuterHeight = $('.docs-nav').height();

                    return (this.top = offsetTop - navOuterHeight - sideBarMargin);
                },
                bottom: function () {
                    return (this.bottom = $('div.footer').outerHeight(true));
                }
            }
        });
    }, 100);

    // Config ZeroClipboard
    ZeroClipboard.config({
        moviePath: '_static/ZeroClipboard.swf',
        hoverClass: 'btn-clipboard-hover'
    });

    // Insert copy to clipboard button before .highlight or .example
    $('.highlight-html, .highlight-scss').each(function () {
        var highlight = $(this);
        var previous = highlight.prev();
        var btnHtml = '<div class="zero-clipboard"><span class="btn-clipboard">Copy</span></div>';

        if (previous.hasClass('example')) {
            previous.before(btnHtml.replace(/btn-clipboard/, 'btn-clipboard with-example'));
        } else {
            highlight.before(btnHtml);
        }
    });
    var zeroClipboard = new ZeroClipboard($('.btn-clipboard'));
    var htmlBridge = $('#global-zeroclipboard-html-bridge');

    // Handlers for ZeroClipboard
    zeroClipboard.on('load', function () {
        htmlBridge
            .data('placement', 'top')
            .attr('title', 'Copy to clipboard')
            .tooltip();
    });

    // Copy to clipboard
    zeroClipboard.on('dataRequested', function (client) {
        var highlight = $(this).parent().nextAll('.highlight').first();
        client.setText(highlight.text());
    });

    // Notify copy success and reset tooltip title
    zeroClipboard.on('complete', function () {
        htmlBridge
            .attr('title', 'Copied!')
            .tooltip('fixTitle')
            .tooltip('show')
            .attr('title', 'Copy to clipboard')
            .tooltip('fixTitle');
    });

    // Notify copy failure
    zeroClipboard.on('noflash wrongflash', function () {
        htmlBridge.attr('title', 'Flash required')
            .tooltip('fixTitle')
            .tooltip('show');
    });
});
