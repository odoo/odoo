// Change address font-size if needed
document.addEventListener('DOMContentLoaded', function (evt) {
    var recipientAddress = document.getElementsByClassName('address row')[0].getElementsByTagName('address')[0];
    var height = parseFloat(window.getComputedStyle(recipientAddress, null).getPropertyValue('height'));
    var fontSize = parseFloat(window.getComputedStyle(recipientAddress, null).getPropertyValue('font-size'));
    recipientAddress.style.fontSize = (85/height) * fontSize + 'px';
});
