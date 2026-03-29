// Change address font-size if needed
document.addEventListener('DOMContentLoaded', function (evt) {
    var recipientAddress = document.querySelector(".address.row > div[name='address'] > address");
    let baseSize = 120;
    if (!recipientAddress) {
        recipientAddress = document.querySelector("div .row.fallback_header > div.col-5.offset-7 > div:first-child");
    }
    var style = window.getComputedStyle(recipientAddress, null); 
    var height = parseFloat(style.getPropertyValue('height'));
    var fontSize = parseFloat(style.getPropertyValue('font-size'));
    recipientAddress.style.fontSize = (baseSize / (height / fontSize)) + 'px';
});
