
var FormDataMirrorClient = (function(){

    function FormDataMirrorClient(mirror){
        this.mirror = mirror;
    };

    FormDataMirrorClient.prototype._create_mutation = function(el) {
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
        return arg;
    };

    FormDataMirrorClient.prototype.setData = function() {
        var self = this;
        var elems = [];
        $elements = $('input, textarea, select');
        // detect input changes
        $elements.change(function(e) {
            if(e.srcElement){
                var change = self._create_mutation(e.srcElement);
                var index = $elements.index(e.srcElement);
                change["_index"] = index;
                self.mirror.setData([change]);
            }
        });
        // detect initial input values
        _.each($elements, function(el){
            elems.push(self._create_mutation(el));
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
            var index = el._index ? el._index : i;
            if(el.tagName === 'INPUT'){
                if(el.type === "text"){
                    $elements[index].value = el.value
                }
                if(el.type === 'checkbox' || el.type === 'radio'){
                    $elements[index].checked = el.value;
                }
            }
            if(el.tagName === 'TEXTEAREA'){
                $elements[index].value = el.value;
            }
            if(el.tagName === 'SELECT'){
                $elements[index].selectedIndex = el.value;
            }
        });
    };
    return FormDataMirror;
})();

