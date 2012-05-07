(function() {

var
  D = Flotr.DOM,
  _ = Flotr._;

function getImage (type, canvas, width, height) {

  // TODO add scaling for w / h
  var
    mime = 'image/'+type,
    data = canvas.toDataURL(mime),
    image = new Image();
  image.src = data;
  return image;
}

Flotr.addPlugin('download', {

  saveImage: function (type, width, height, replaceCanvas) {
    var image = null;
    if (Flotr.isIE && Flotr.isIE < 9) {
      image = '<html><body>'+this.canvas.firstChild.innerHTML+'</body></html>';
      return window.open().document.write(image);
    }

    if (type !== 'jpeg' && type !== 'png') return;

    image = getImage(type, this.canvas, width, height);

    if (_.isElement(image) && replaceCanvas) {
      this.download.restoreCanvas();
      D.hide(this.canvas);
      D.hide(this.overlay);
      D.setStyles({position: 'absolute'});
      D.insert(this.el, image);
      this.saveImageElement = image;
    } else {
      return window.open(image.src);
    }
  },

  restoreCanvas: function() {
    D.show(this.canvas);
    D.show(this.overlay);
    if (this.saveImageElement) this.el.removeChild(this.saveImageElement);
    this.saveImageElement = null;
  }
});

})();
