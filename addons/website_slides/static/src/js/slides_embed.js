/*global $, openerp, _, PDFJS */
$(document).ready(function () {

if ($('#pdfcanvas').length) {
    PDFJS.disableWorker = true;

    var pdfDoc = null,
        pageNum = 1,
        pageRendering = false,
        pageNumPending = null,
        scale = 1.5,
        url = $('#pdf_file').val(),
        canvas = $('#pdfcanvas').get(0),
        ctx = canvas.getContext('2d'),
        PDFViewer = {};

    PDFViewer.renderPage =  function(num) {
        pageRendering = true;
        // Using promise to fetch the page
        pdfDoc.getPage(num).then(function(page) {
            var viewport = page.getViewport(scale);
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            // Render PDF page into canvas context
            var renderContext = {
                canvasContext: ctx,
                viewport: viewport
            };
            var renderTask = page.render(renderContext);
            // Wait for rendering to finish
            renderTask.promise.then(function () {
                pageRendering = false;
                if (pageNumPending !== null) {
                    // New page rendering is pending
                    PDFViewer.renderPage(pageNumPending);
                    pageNumPending = null;
                }
            });
        });
        // Update page counters
        $('#page_number').val(pageNum);
        //Hide all slide option on page render
        $('.slide-option-toggle').hide();
    };

    PDFViewer.queueRenderPage = function(num) {
        if (pageRendering) {
            pageNumPending = num;
        } else {
            PDFViewer.renderPage(num);
        }
    };

    PDFViewer.onPrevPage = function() {
        if (pageNum <= 1) {
            return;
        }
        pageNum--;
        PDFViewer.queueRenderPage(pageNum);
    };
    $('#previous').on('click', function () { PDFViewer.onPrevPage(); });

    PDFViewer.onNextPage = function() {
        if (pageNum === pdfDoc.numPages) {
            $('.slide-option-toggle').hide();
            $("#slide_suggest").slideToggle();
        }
        if (pageNum >= pdfDoc.numPages) {
            return;
        }
        pageNum++;
        PDFViewer.queueRenderPage(pageNum);
    };
    $('#next').on('click', function () { PDFViewer.onNextPage(); });

    PDFViewer.onLastPage = function() {
        pageNum = pdfDoc.numPages;
        PDFViewer.queueRenderPage(pdfDoc.numPages);
    };
    $('#last').on('click', function () { PDFViewer.onLastPage(); });

    PDFViewer.onFirstPage = function() {
        pageNum = 1;
        PDFViewer.queueRenderPage(1);
    };
    $('#first').on('click', function () { PDFViewer.onFirstPage(); });

    PDFViewer.onPagecSearch = function() {
        var currentVal = parseInt($('#page_number').val());
        if(currentVal > 0 && currentVal <= pdfDoc.numPages){
            pageNum = currentVal;
            PDFViewer.renderPage(pageNum);
        }else{
            $('#page_number').val(pageNum);
        }
    };
    $('#page_number').on('change', function () { PDFViewer.onPagecSearch(); });

    PDFViewer.toggleFullScreen  = function() {
        var elem = $("#pdfcanvas").get(0);
        if (!elem.fullscreenElement && !elem.mozFullScreenElement && !elem.webkitFullscreenElement && !elem.msFullscreenElement ) {
            if (elem.requestFullscreen) {
                elem.requestFullscreen();
            } else if (elem.msRequestFullscreen) {
                elem.msRequestFullscreen();
            } else if (elem.mozRequestFullScreen) {
                elem.mozRequestFullScreen();
            } else if (elem.webkitRequestFullscreen) {
                elem.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
            }
        } else {
            if (elem.exitFullscreen) {
                elem.exitFullscreen();
            } else if (elem.msExitFullscreen) {
                elem.msExitFullscreen();
            } else if (elem.mozCancelFullScreen) {
                elem.mozCancelFullScreen();
            } else if (elem.webkitExitFullscreen) {
                elem.webkitExitFullscreen();
            }
        }
    };
    $('#fullscreen').on('click', function(){ PDFViewer.toggleFullScreen(); });

    PDFViewer.set_embed_page = function(page) {
        var $embed_input = $('.slide_embed_code');
        var slide_embed_code = $embed_input.val();
        var tmp_embed_code = slide_embed_code.replace(/(page=).*?([^\d]+)/,'$1' + page + '$2');
        $embed_input.val(tmp_embed_code);
    };

    $('.embed-page-counter').on('change', function(e){
        e.preventDefault();
        var page = parseInt($(this).val());
        var maxval = parseInt($('#page_count').text());
        if(page > 0 && page <= maxval){
            PDFViewer.set_embed_page(page);
        }else{
            $(this).val(1);
            PDFViewer.set_embed_page(1);
        }
    });

    $(document).keydown(function (ev) {
        if (ev.keyCode == 37) {
            PDFViewer.onPrevPage();
        }
        if (ev.keyCode == 39) {
            PDFViewer.onNextPage();
        }
    });

    PDFJS.getDocument(url).then(function (pdfDoc_) {
        pdfDoc = pdfDoc_;
        $('#page_count').text(pdfDoc.numPages);
        var initpage = parseInt($('#pdf_page').val());
        pageNum = (initpage > 0 && initpage <= pdfDoc.numPages)? initpage : 1;
        // Initial/first page rendering
        PDFViewer.renderPage(pageNum);
        $('#slide_init_image').hide();
        $('#pdfcanvas').show();
    });
}

$('.toggle-slide-option').on('click', function (ev) {
    ev.preventDefault();
    var toggleDiv = $(this).data('slide-option-id');
    $('.slide-option-toggle').not(toggleDiv).each(function() {
        $(this).hide();
    });
    $(toggleDiv).slideToggle();
});

$('.oe_slides_pdf_js_thumb').hover(
    function () {
        $(this).find('.oe_slides_pdf_js_caption').stop().slideDown(250);
    },
    function () {
        $(this).find('.oe_slides_pdf_js_caption').stop().slideUp(250);
    }
);

$.post( "/slides/embed/count", {
    slide: parseInt($('#pdf_id').val()),
    url: document.referrer
});

// We do not add openerpframework.js dependency so use jquery ajax
// to post data instead of openerp.jsonRpc
$('.oe_slide_js_share_email').on('click', function () {
    var $input = $(this).parent().prev(':input');
    if (!$input.val() || !$input[0].checkValidity()) {
        $input.closest('.form-group').addClass('has-error');
        $input.focus();
        return;
    }
    $input.closest('.form-group').removeClass('has-error');
    $.ajax({
        type: "POST",
        dataType: 'json',
        url: '/slides/slide/' + $(this).attr('slide-id') + '/send_share_email',
        contentType: "application/json; charset=utf-8",
        data: JSON.stringify({'jsonrpc': "2.0", 'method': "call", "params": {'email': $input.val()}}),
        success: function () {
            $input.closest('.form-group').html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
        }
    });
});

});