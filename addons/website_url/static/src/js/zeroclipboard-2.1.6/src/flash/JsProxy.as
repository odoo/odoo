package {

  import flash.external.ExternalInterface;
  import flash.net.navigateToURL;
  import flash.net.URLRequest;


  /**
   * An abstraction for communicating with JavaScript from Flash.
   */
  internal class JsProxy {
    private var hosted:Boolean = false;
    private var bidirectional:Boolean = false;
    private var disabled:Boolean = false;


    /**
     * @constructor
     */
    public function JsProxy(expectedObjectId:String = null) {
      // The JIT Compiler does not compile constructors, so any
      // cyclomatic complexity higher than 1 is discouraged.
      this.ctor(expectedObjectId);
    }


    /**
     * The real constructor.
     *
     * @return `undefined`
     */
    private function ctor(expectedObjectId:String = null): void {
      // Do we authoritatively know that this Flash object is hosted in a browser?
      this.hosted = ExternalInterface.available === true &&
        ExternalInterface.objectID &&
        (expectedObjectId ? (expectedObjectId === ExternalInterface.objectID) : true);

      // Can we retrieve values from JavaScript?
      // Try this regardless of the return value of `ExternalInterface.call`.
      try {
        this.bidirectional = ExternalInterface.call("(function() { return true; })") === true;
      }
      catch (e:Error) {
        // We do NOT authoritatively know if this Flash object is hosted in a browser,
        // nor if JavaScript is disabled.
        this.bidirectional = false;
      }

      // If hosted but cannot bidirectionally communicate with JavaScript,
      // then JavaScript is disabled on the page!
      this.disabled = this.hosted && !this.bidirectional;
    }


    /**
     * Are we authoritatively certain that we can execute JavaScript bidirectionally?
     *
     * @return Boolean
     */
    public function isComplete(): Boolean {
      return this.hosted && this.bidirectional;
    }


    /**
     * Register an ActionScript method as callable from the container's JavaScript
     *
     * This will execute the JavaScript ONLY if ExternalInterface is completely
     * available (hosted in the browser AND supporting bidirectional communication).
     *
     * @return `undefined`
     */
    public function addCallback(functionName:String, closure:Function): void {
      if (this.isComplete()) {
        ExternalInterface.addCallback(functionName, closure);
      }
    }

    /**
     * Execute a function expression or named function, with optional arguments,
     * and receive its return value.
     *
     * This will execute the JavaScript ONLY if ExternalInterface is completely
     * available (hosted in the browser AND supporting bidirectional communication).
     *
     * @example
     * var jsProxy:JsProxy = new JsProxy("global-zeroclipboard-flash-bridge");
     * var result:Object = jsProxy.call("ZeroClipboard.emit", [{ type: "copy" }]);
     * jsProxy.call("(function(eventObj) { return ZeroClipboard.emit(eventObj); })", [{ type: "ready"}]);
     *
     * @return `undefined`, or anything
     */
    public function call(
      jsFuncExpr:String,
      args:Array = null
    ): * {  // NOPMD
      var result:* = undefined;  // NOPMD
      if (jsFuncExpr && this.isComplete()) {
        if (args == null) {
          args = [];
        }
        result = ExternalInterface.call.apply(ExternalInterface, [jsFuncExpr].concat(args));
      }
      return result;
    }


    /**
     * Execute a function expression or named function, with optional arguments.
     * No return values will ever be received.
     *
     * This will attempt to execute the JavaScript, even if ExternalInterface is
     * not available; in which case: the worst thing that can happen is that
     * the JavaScript is not executed (i.e. if JavaScript is disabled, or if
     * the SWF is not allowed to communicate with JavaScript on its host page).
     *
     * @return `undefined`
     */
    public function send(jsFuncExpr:String, args:Array = null): void {
      if (jsFuncExpr) {
        if (this.isComplete()) {
          this.call(jsFuncExpr, args);
        }
        else if (!this.disabled) {
          if (args == null) {
            args = [];
          }
          var argsStr:String = "";
          for (var counter:int = 0; counter < args.length; counter++) {
            argsStr += JSON.stringify(args[counter]);
            if ((counter + 1) < args.length) {
              argsStr += ", ";
            }
          }
          navigateToURL(new URLRequest("javascript:" + jsFuncExpr + "(" + argsStr + ");"), "_self");
        }
      }
    }
  }
}