
function openerp_pos_keyboard(instance, module){ //module is instance.point_of_sale
// ---------- OnScreen Keyboard Widget ----------

    // A Widget that displays an onscreen keyboard.
    // There are two options when creating the widget :
    // 
    // * 'keyboard_model' : 'simple' | 'full' (default) 
    //   The 'full' emulates a PC keyboard, while 'simple' emulates an 'android' one.
    //
    // * 'input_selector  : (default: '.searchbox input') 
    //   defines the dom element that the keyboard will write to.
    // 
    // The widget is initially hidden. It can be shown with this.show(), and is 
    // automatically shown when the input_selector gets focused.

    module.OnscreenKeyboardWidget = instance.web.Widget.extend({
        template: 'OnscreenKeyboardSimple', 
        init: function(parent, options){
            var self = this;
            this._super(parent,options);
            options = options || {};

            this.keyboard_model = options.keyboard_model || 'full';
            if(this.keyboard_model === 'full'){
                this.template = 'OnscreenKeyboardFull';
            }

            this.input_selector = options.input_selector || '.searchbox input';
            this.$target = null;

            //Keyboard state
            this.capslock = false;
            this.shift    = false;
            this.numlock  = false;
        },
        
        connect : function(target){
            var self = this;
            this.$target = $(target);
            this.$target.focus(function(){self.show();});
        },
        generateEvent: function(type,key){
            var event = document.createEvent("KeyboardEvent");
            var initMethod =  event.initKeyboardEvent ? 'initKeyboardEvent' : 'initKeyEvent';
            event[initMethod](  type,
                                true, //bubbles
                                true, //cancelable
                                window, //viewArg
                                false, //ctrl
                                false, //alt
                                false, //shift
                                false, //meta
                                ((typeof key.code === 'undefined') ? key.char.charCodeAt(0) : key.code),
                                ((typeof key.char === 'undefined') ? String.fromCharCode(key.code) : key.char)
                            );
            return event;

        },

        // Write a character to the input zone
        writeCharacter: function(character){
            var input = this.$target[0];
            input.dispatchEvent(this.generateEvent('keydown',{char: character}));
            if(character !== '\n'){
                input.value += character;
            }
            input.dispatchEvent(this.generateEvent('keyup',{char: character}));
        },
        
        // Removes the last character from the input zone.
        deleteCharacter: function(){
            var input = this.$target[0];
            input.dispatchEvent(this.generateEvent('keydown',{code: 8}));
            input.value = input.value.substr(0, input.value.length -1);
            input.dispatchEvent(this.generateEvent('keyup',{code: 8}));
        },
        
        // Clears the content of the input zone.
        deleteAllCharacters: function(){
            var input = this.$target[0];
            if(input.value){
                input.dispatchEvent(this.generateEvent('keydown',{code: 8}));
                input.value = "";
                input.dispatchEvent(this.generateEvent('keyup',{code: 8}));
            }
        },

        // Makes the keyboard show and slide from the bottom of the screen.
        show:  function(){
            $('.keyboard_frame').show().css({'height':'235px'});
        },
        
        // Makes the keyboard hide by sliding to the bottom of the screen.
        hide:  function(){
            $('.keyboard_frame')
                .css({'height':'0'})
                .hide();
            this.reset();
        },
        
        //What happens when the shift key is pressed : toggle case, remove capslock
        toggleShift: function(){
            $('.letter').toggleClass('uppercase');
            $('.symbol span').toggle();
            
            self.shift = (self.shift === true) ? false : true;
            self.capslock = false;
        },
        
        //what happens when capslock is pressed : toggle case, set capslock
        toggleCapsLock: function(){
            $('.letter').toggleClass('uppercase');
            self.capslock = true;
        },
        
        //What happens when numlock is pressed : toggle symbols and numlock label 
        toggleNumLock: function(){
            $('.symbol span').toggle();
            $('.numlock span').toggle();
            self.numlock = (self.numlock === true ) ? false : true;
        },

        //After a key is pressed, shift is disabled. 
        removeShift: function(){
            if (self.shift === true) {
                $('.symbol span').toggle();
                if (this.capslock === false) $('.letter').toggleClass('uppercase');
                
                self.shift = false;
            }
        },

        // Resets the keyboard to its original state; capslock: false, shift: false, numlock: false
        reset: function(){
            if(this.shift){
                this.toggleShift();
            }
            if(this.capslock){
                this.toggleCapsLock();
            }
            if(this.numlock){
                this.toggleNumLock();
            }
        },

        //called after the keyboard is in the DOM, sets up the key bindings.
        start: function(){
            var self = this;

            //this.show();


            $('.close_button').click(function(){ 
                self.deleteAllCharacters();
                self.hide(); 
            });

            // Keyboard key click handling
            $('.keyboard li').click(function(){
                
                var $this = $(this),
                    character = $this.html(); // If it's a lowercase letter, nothing happens to this variable
                
                if ($this.hasClass('left-shift') || $this.hasClass('right-shift')) {
                    self.toggleShift();
                    return false;
                }
                
                if ($this.hasClass('capslock')) {
                    self.toggleCapsLock();
                    return false;
                }
                
                if ($this.hasClass('delete')) {
                    self.deleteCharacter();
                    return false;
                }

                if ($this.hasClass('numlock')){
                    self.toggleNumLock();
                    return false;
                }
                
                // Special characters
                if ($this.hasClass('symbol')) character = $('span:visible', $this).html();
                if ($this.hasClass('space')) character = ' ';
                if ($this.hasClass('tab')) character = "\t";
                if ($this.hasClass('return')) character = "\n";
                
                // Uppercase letter
                if ($this.hasClass('uppercase')) character = character.toUpperCase();
                
                // Remove shift once a key is clicked.
                self.removeShift();

                self.writeCharacter(character);
            });
        },
    });
}
