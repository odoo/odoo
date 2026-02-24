$.fn.loadTemplates = function() {
  $.JST.loadTemplates($(this));
  return this;
};

$.JST = {
  _templates: new Object(),
  _decorators:new Object(),

  loadTemplates: function(elems) {
    elems.each(function() {
      $(this).find(".__template__").each(function() {
    	  console.log('templat------------------')
          var tmpl = $(this);
          var type = tmpl.attr("type");

          //template may be inside <!-- ... --> or not in case of ajax loaded templates
          var found=false;
          var el=tmpl.get(0).firstChild;
          while (el && !found) {
            if (el.nodeType == 8) { // 8==comment
              var templateBody = el.nodeValue; // this is inside the comment
              found=true;
              break;
            }
            el=el.nextSibling;
          }
          if (!found)
            var templateBody = tmpl.html(); // this is the whole template

          if (!templateBody.match(/##\w+##/)) { // is Resig' style? e.g. (#=id#) or (# ...some javascript code 'obj' is the alias for the object #)
            var strFunc =
                    "var p=[],print=function(){p.push.apply(p,arguments);};" +
                    "with(obj){p.push('" +
                    templateBody.replace(/[\r\t\n]/g, " ")
                            .replace(/'(?=[^#]*#\))/g, "\t")
                            .split("'").join("\\'")
                            .split("\t").join("'")
                            .replace(/\(#=(.+?)#\)/g, "',$1,'")
                            .split("(#").join("');")
                            .split("#)").join("p.push('")
                            + "');}return p.join('');";

          try {
            $.JST._templates[type] = new Function("obj", strFunc);
          } catch (e) {
            console.error("JST error: "+type, e,strFunc);
          }

          } else { //plain template   e.g. ##id##
          try {
            $.JST._templates[type] = templateBody;
          } catch (e) {
            console.error("JST error: "+type, e,templateBody);
          }
          }

          tmpl.remove();

      });
    });
  },

  createFromTemplate: function(jsonData, template, transformToPrintable) {
    var templates = $.JST._templates;

    var jsData=new Object();
    if (transformToPrintable){
      for (var prop in jsonData){
        var value = jsonData[prop];
        if (typeof(value) == "string")
          value = (value + "").replace(/\n/g, "<br>");
        jsData[prop]=value;
      }
    } else {
      jsData=jsonData;
    }

    function fillStripData(strip, data) {
      for (var prop in data) {
        var value = data[prop];

        strip = strip.replace(new RegExp("##" + prop + "##", "gi"), value);
      }
      // then clean the remaining ##xxx##
      strip = strip.replace(new RegExp("##\\w+##", "gi"), "");
      return strip;
    }

    var stripString = "";
    if (typeof(template) == "undefined") {
      alert("Template is required");
      stripString = "<div>Template is required</div>";

    } else if (typeof(templates[template]) == "function") { // resig template
      try {
        stripString = templates[template](jsData);// create a jquery object in memory
      } catch (e) {
        console.error("JST error: "+template,e.message);
        stripString = "<div> ERROR: "+template+"<br>" + e.message + "</div>";
      }

    } else {
      stripString = templates[template]; // recover strip template
      if (!stripString || stripString.trim() == "") {
        console.error("No template found for type '" + template + "'");
        return $("<div>");

      } else {
        stripString = fillStripData(stripString, jsData); //replace placeholders with data
      }
    }

    var ret = $(stripString);// create a jquery object in memory
    ret.attr("__template", template); // set __template attribute

    //decorate the strip
    var dec = $.JST._decorators[template];
    if (typeof (dec) == "function")
      dec(ret, jsData);

    return ret;
  },


  existsTemplate: function(template) {
    return $.JST._templates[template];
  },

  //decorate function is like function(domElement,jsonData){...}
  loadDecorator:function(template, decorator) {
    $.JST._decorators[template] = decorator;
  },

  getDecorator:function(template) {
    return $.JST._decorators[template];
  },

  decorateTemplate:function(element) {
    var dec = $.JST._decorators[element.attr("__template")];
    if (typeof (dec) == "function")
      dec(editor);
  },

  // asynchronous
  ajaxLoadAsynchTemplates: function(templateUrl, callback) {

    $.get(templateUrl, function(data) {

      var div = $("<div>");
      div.html(data);

      $.JST.loadTemplates(div);

      if (typeof(callback == "function"))
        callback();
    },"html");
  },

  ajaxLoadTemplates: function(templateUrl) {
    $.ajax({
      async:false,
      url: templateUrl,
      dataType: "html",
      success: function(data) {
        var div = $("<div>");
        div.html(data);
        $.JST.loadTemplates(div);
      }
    });

  }


};
