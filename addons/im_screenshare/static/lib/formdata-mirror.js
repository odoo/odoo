
var FormDataMirrorClient = (function(){

    function FormDataMirrorClient(mirror){
        this.mirror = mirror;
    };

    FormDataMirrorClient.prototype.setData = function() {
        var elems = [];
        _.each($('input, textarea, select'), function(el){
            var arg = {
                id : el.id,
                tagName: el.tagName
            };
            if(el.tagName === 'INPUT'){
                arg['type'] = el.type;
                if(el.type === "text"){
                    arg['value'] = el.value;
                }
                if(el.type === 'checkbox' || el.type === 'radio'){
                    arg['value'] = el.checked ? true : false;
                }
            }
            if(el.tagName === 'TEXTEAREA'){
                arg['value'] = el.value;
            }
            if(el.tagName === 'SELECT'){
                arg['value'] = el.selectedIndex;
            }
            elems.push(arg);
        });
        this.mirror.setData(elems);
    };
    return FormDataMirrorClient;
})();



var FormDataMirror = (function(){

    function FormDataMirror(){};

    FormDataMirror.prototype.formData = function(data) {
        var $elements = $('input, textarea, select');
        _.each(data, function(el, i){
            if(el.tagName === 'INPUT'){
                if(el.type === "text"){
                    $elements[i].value = el.value
                }
                if(el.type === 'checkbox' || el.type === 'radio'){
                    $elements[i].checked = el.value;
                }
            }
            if(el.tagName === 'TEXTEAREA'){
                $elements[i].value = el.value;
            }
            if(el.tagName === 'SELECT'){
                console.log($elements[i]);
                $elements[i].selectedIndex = el.value;
            }
        });
    };
    return FormDataMirror;
})();

