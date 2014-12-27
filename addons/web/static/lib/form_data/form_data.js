window.FormDataCompatibility = (function() {

  function FormDataCompatibility(form) {
    this.fields = {};
    this.boundary = this.generateBoundary();
    this.contentType = "multipart/form-data; boundary=" + this.boundary;
    this.CRLF = "\r\n";

    if (typeof form !== 'undefined') {
      for (var i = 0; i < form.elements.length; i++) {
        var e = form.elements[i];
  // If not set, the element's name is auto-generated
        var name = (e.name !== null && e.name !== '') ? e.name : this.getElementNameByIndex(i);
        this.append(name, e);
      }
    }
  }

  FormDataCompatibility.prototype.getElementNameByIndex = function(index) {
    return '___form_element__' + index; // Strange enough to avoid collision with user-defined names
  }

  FormDataCompatibility.prototype.append = function(key, value) {
    return this.fields[key] = value;
  };

  FormDataCompatibility.prototype.setContentTypeHeader = function(xhr) {
    return xhr.setRequestHeader("Content-Type", this.contentType);
  };

  FormDataCompatibility.prototype.getContentType = function() {
    return this.contentType;
  };

  FormDataCompatibility.prototype.generateBoundary = function() {
    return "AJAX--------------" + ((new Date).getTime());
  };

  FormDataCompatibility.prototype.buildBody = function() {
    var body, key, parts, value, _ref;
    parts = [];
    _ref = this.fields;
    for (key in _ref) {
      value = _ref[key];
      parts.push(this.buildPart(key, value));
    }
    body = "--" + this.boundary + this.CRLF;
    body += parts.join("--" + this.boundary + this.CRLF);
    body += "--" + this.boundary + "--" + this.CRLF;
    return body;
  };

  FormDataCompatibility.prototype.buildPart = function(key, value) {
    var part;
    if (typeof value === "string") {
      part = "Content-Disposition: form-data; name=\"" + key + "\"" + this.CRLF;
      part += "Content-Type: text/plain; charset=utf-8" + this.CRLF + this.CRLF;
      part += unescape(encodeURIComponent(value)) + this.CRLF;  // UTF-8 encoded like in real FormData
    } else if (typeof value === typeof File) {
        part = "Content-Disposition: form-data; name=\"" + key + "\"; filename=\"" + value.fileName + "\"" + this.CRLF;
        part += "Content-Type: " + value.type + this.CRLF + this.CRLF;
        part += value.getAsBinary() + this.CRLF;
    } else if (typeof value === typeof HTMLInputElement) {
      if (value.type == 'file') {
        // Unsupported
      } else {
        part = "Content-Disposition: form-data; name=\"" + key + "\"" + this.CRLF;
        part += "Content-Type: text/plain; charset=utf-8" + this.CRLF + this.CRLF;
        part += unescape(encodeURIComponent(value.value)) + this.CRLF;  // UTF-8 encoded like in real FormData
      }
    } else if (typeof value === 'object' && typeof value.value === 'string') {  // IE7 path
        part = "Content-Disposition: form-data; name=\"" + key + "\"" + this.CRLF;
        part += "Content-Type: text/plain; charset=utf-8" + this.CRLF + this.CRLF;
        part += unescape(encodeURIComponent(value.value)) + this.CRLF;  // UTF-8 encoded like in real FormData
    }
    return part;
  };

  return FormDataCompatibility;

})();