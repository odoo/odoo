/*
 * Canvas2Image v0.1
 * Copyright (c) 2008 Jacob Seidelin, cupboy@gmail.com
 * MIT License [http://www.opensource.org/licenses/mit-license.php]
 */

var Canvas2Image = (function() {
  // check if we have canvas support
  var oCanvas = document.createElement("canvas"),
      sc = String.fromCharCode,
      strDownloadMime = "image/octet-stream",
      bReplaceDownloadMime = false;
  
  // no canvas, bail out.
  if (!oCanvas.getContext) {
    return {
      saveAsBMP : function(){},
      saveAsPNG : function(){},
      saveAsJPEG : function(){}
    }
  }

  var bHasImageData = !!(oCanvas.getContext("2d").getImageData),
      bHasDataURL = !!(oCanvas.toDataURL),
      bHasBase64 = !!(window.btoa);

  // ok, we're good
  var readCanvasData = function(oCanvas) {
    var iWidth = parseInt(oCanvas.width),
        iHeight = parseInt(oCanvas.height);
    return oCanvas.getContext("2d").getImageData(0,0,iWidth,iHeight);
  }

  // base64 encodes either a string or an array of charcodes
  var encodeData = function(data) {
    var i, aData, strData = "";
    
    if (typeof data == "string") {
      strData = data;
    } else {
      aData = data;
      for (i = 0; i < aData.length; i++) {
        strData += sc(aData[i]);
      }
    }
    return btoa(strData);
  }

  // creates a base64 encoded string containing BMP data takes an imagedata object as argument
  var createBMP = function(oData) {
    var strHeader = '',
        iWidth = oData.width,
        iHeight = oData.height;

    strHeader += 'BM';
  
    var iFileSize = iWidth*iHeight*4 + 54; // total header size = 54 bytes
    strHeader += sc(iFileSize % 256); iFileSize = Math.floor(iFileSize / 256);
    strHeader += sc(iFileSize % 256); iFileSize = Math.floor(iFileSize / 256);
    strHeader += sc(iFileSize % 256); iFileSize = Math.floor(iFileSize / 256);
    strHeader += sc(iFileSize % 256);

    strHeader += sc(0, 0, 0, 0, 54, 0, 0, 0); // data offset
    strHeader += sc(40, 0, 0, 0); // info header size

    var iImageWidth = iWidth;
    strHeader += sc(iImageWidth % 256); iImageWidth = Math.floor(iImageWidth / 256);
    strHeader += sc(iImageWidth % 256); iImageWidth = Math.floor(iImageWidth / 256);
    strHeader += sc(iImageWidth % 256); iImageWidth = Math.floor(iImageWidth / 256);
    strHeader += sc(iImageWidth % 256);
  
    var iImageHeight = iHeight;
    strHeader += sc(iImageHeight % 256); iImageHeight = Math.floor(iImageHeight / 256);
    strHeader += sc(iImageHeight % 256); iImageHeight = Math.floor(iImageHeight / 256);
    strHeader += sc(iImageHeight % 256); iImageHeight = Math.floor(iImageHeight / 256);
    strHeader += sc(iImageHeight % 256);
  
    strHeader += sc(1, 0, 32, 0); // num of planes & num of bits per pixel
    strHeader += sc(0, 0, 0, 0); // compression = none
  
    var iDataSize = iWidth*iHeight*4; 
    strHeader += sc(iDataSize % 256); iDataSize = Math.floor(iDataSize / 256);
    strHeader += sc(iDataSize % 256); iDataSize = Math.floor(iDataSize / 256);
    strHeader += sc(iDataSize % 256); iDataSize = Math.floor(iDataSize / 256);
    strHeader += sc(iDataSize % 256); 
  
    strHeader += sc(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0); // these bytes are not used
  
    var aImgData = oData.data,
        strPixelData = "",
        c, x, y = iHeight,
        iOffsetX, iOffsetY, strPixelRow;
    
    do {
      iOffsetY = iWidth*(y-1)*4;
      strPixelRow = "";
      for (x = 0; x < iWidth; x++) {
        iOffsetX = 4*x;
        strPixelRow += sc(
          aImgData[iOffsetY + iOffsetX + 2], // B
          aImgData[iOffsetY + iOffsetX + 1], // G
          aImgData[iOffsetY + iOffsetX],     // R
          aImgData[iOffsetY + iOffsetX + 3]  // A
        );
      }
      strPixelData += strPixelRow;
    } while (--y);

    return encodeData(strHeader + strPixelData);
  }

  // sends the generated file to the client
  var saveFile = function(strData) {
    if (!window.open(strData)) {
      document.location.href = strData;
    }
  }

  var makeDataURI = function(strData, strMime) {
    return "data:" + strMime + ";base64," + strData;
  }

  // generates a <img> object containing the imagedata
  var makeImageObject = function(strSource) {
    var oImgElement = document.createElement("img");
    oImgElement.src = strSource;
    return oImgElement;
  }

  var scaleCanvas = function(oCanvas, iWidth, iHeight) {
    if (iWidth && iHeight) {
      var oSaveCanvas = document.createElement("canvas");
      
      oSaveCanvas.width = iWidth;
      oSaveCanvas.height = iHeight;
      oSaveCanvas.style.width = iWidth+"px";
      oSaveCanvas.style.height = iHeight+"px";

      var oSaveCtx = oSaveCanvas.getContext("2d");

      oSaveCtx.drawImage(oCanvas, 0, 0, oCanvas.width, oCanvas.height, 0, 0, iWidth, iWidth);
      
      return oSaveCanvas;
    }
    return oCanvas;
  }

  return {
    saveAsPNG : function(oCanvas, bReturnImg, iWidth, iHeight) {
      if (!bHasDataURL) return false;
      
      var oScaledCanvas = scaleCanvas(oCanvas, iWidth, iHeight),
          strMime = "image/png",
          strData = oScaledCanvas.toDataURL(strMime);
        
      if (bReturnImg) {
        return makeImageObject(strData);
      } else {
        saveFile(bReplaceDownloadMime ? strData.replace(strMime, strDownloadMime) : strData);
      }
      return true;
    },

    saveAsJPEG : function(oCanvas, bReturnImg, iWidth, iHeight) {
      if (!bHasDataURL) return false;

      var oScaledCanvas = scaleCanvas(oCanvas, iWidth, iHeight),
          strMime = "image/jpeg",
          strData = oScaledCanvas.toDataURL(strMime);
  
      // check if browser actually supports jpeg by looking for the mime type in the data uri. if not, return false
      if (strData.indexOf(strMime) != 5) return false;

      if (bReturnImg) {
        return makeImageObject(strData);
      } else {
        saveFile(bReplaceDownloadMime ? strData.replace(strMime, strDownloadMime) : strData);
      }
      return true;
    },

    saveAsBMP : function(oCanvas, bReturnImg, iWidth, iHeight) {
      if (!(bHasDataURL && bHasImageData && bHasBase64)) return false;

      var oScaledCanvas = scaleCanvas(oCanvas, iWidth, iHeight),
          strMime = "image/bmp",
          oData = readCanvasData(oScaledCanvas),
          strImgData = createBMP(oData);
        
      if (bReturnImg) {
        return makeImageObject(makeDataURI(strImgData, strMime));
      } else {
        saveFile(makeDataURI(strImgData, strMime));
      }
      return true;
    }
  };
})();