package {

  import flash.system.Capabilities;
  import flash.system.System;
  import flash.desktop.Clipboard;
  import flash.desktop.ClipboardFormats;
  import flash.utils.ByteArray;


  /**
   * An abstraction for injecting data into the user's clipboard.
   */
  internal class ClipboardInjector {
    /**
     * Use the fancy "Desktop" clipboard for expanded text support (e.g. HTML, RTF, etc.) if not on Linux
     */
    private var useEnhancedClipboard:Boolean = Capabilities.os.slice(0, 5).toLowerCase() !== "linux";


    /**
     * @constructor
     */
    public function ClipboardInjector(forceEnhancedClipboard:Boolean = false) {
      // The JIT Compiler does not compile constructors, so any
      // cyclomatic complexity higher than 1 is discouraged.
      this.ctor(forceEnhancedClipboard);
    }


    /**
     * The real constructor.
     *
     * @return `undefined`
     */
    private function ctor(forceEnhancedClipboard:Boolean = false): void {
      // Should we use the fancy "Desktop" clipboard for expanded text support (e.g. HTML, RTF, etc.)?
      this.useEnhancedClipboard = this.useEnhancedClipboard || forceEnhancedClipboard;
    }


    /**
     * Inject data into the user's clipboard.
     *
     * @return A clipboard "results" object
     */
    public function inject(
      clipData:Object  // NOPMD
    ): Object {  // NOPMD
      var results:Object = {};  // NOPMD

      // Set all data formats' results to `false` (failed) initially
      for (var dataFormat:String in clipData) {
        if (dataFormat && clipData.hasOwnProperty(dataFormat)) {
          results[dataFormat] = false;
        }
      }

      // If there is any viable data to copy...
      if (ClipboardInjector.hasData(clipData)) {
        // ...and we only need to handle plain text...
        if (!this.useEnhancedClipboard || ClipboardInjector.hasOnlyPlainText(clipData)) {
          this.injectPlainTextOnly(clipData, results);
        }
        // ...else if there is viable data to copy and we can copy enhanced formats
        else if (this.useEnhancedClipboard) {
          this.injectEnhancedData(clipData, results);
        }
      }

      return results;
    }



    /**
     * Inject plain text into the System clipboard (i.e. Flash 9+ Clipboard).
     *
     * @return `undefined`
     */
    private function injectPlainTextOnly(
      clipData:Object,  // NOPMD
      results:Object  // NOPMD
    ): void {
      // Linux currently doesn't use the correct clipboard buffer with the new
      // Flash 10 API, so we need to use this until we can figure out an alternative
      try {
        System.setClipboard(clipData.text);
        results.text = true;
      }
      catch (e:Error) {
        // Yes, this is already set but FlexPMD complains about empty `catch` blocks
        results.text = false;
      }
    }


    /**
     * Inject plain text, HTML, and RTF into the Desktop clipboard (i.e. Flash 10+ Clipboard).
     *
     * @return `undefined`
     */
    private function injectEnhancedData(
      clipData:Object,  // NOPMD
      results:Object  // NOPMD
    ): void {
      // Clear out the clipboard before starting to copy data
      Clipboard.generalClipboard.clear();

      //
      // Handle each data type in succession...
      //
      // Plain text
      if (typeof clipData.text === "string" && clipData.text) {
        try {
          results.text = Clipboard.generalClipboard.setData(ClipboardFormats.TEXT_FORMAT, clipData.text);
        }
        catch (e:Error) {
          results.text = false;
        }
      }

      // HTML
      if (typeof clipData.html === "string" && clipData.html) {
        try {
          results.html = Clipboard.generalClipboard.setData(ClipboardFormats.HTML_FORMAT, clipData.html);
        }
        catch (e:Error) {
          results.html = false;
        }
      }

      // Rich Text (RTF)
      if (typeof clipData.rtf === "string" && clipData.rtf) {
        try {
          var bytes:ByteArray = new ByteArray();
          bytes.writeUTFBytes(clipData.rtf);
          if (bytes && bytes.length > 0) {
            results.rtf = Clipboard.generalClipboard.setData(ClipboardFormats.RICH_TEXT_FORMAT, bytes);
          }
        }
        catch (e:Error) {
          results.rtf = false;
        }
      }
    }


    /**
     * Check if data object contains any keys with associated values that are non-empty Strings.
     *
     * @return Boolean
     */
    private static function hasData(
      clipData:Object  // NOPMD
    ): Boolean {
      return typeof clipData === "object" && clipData &&
        (
          (typeof clipData.text === "string" && clipData.text) ||
          (typeof clipData.html === "string" && clipData.html) ||
          (typeof clipData.rtf  === "string" && clipData.rtf )
        );
    }


    /**
     * Check if a data object's ONLY injectable data is plain text.
     *
     * @return Boolean
     */
    private static function hasOnlyPlainText(
      clipData:Object  // NOPMD
    ): Boolean {
      var hasPlainText:Boolean = false;
      var hasOtherTypes:Boolean = false;
      if (typeof clipData === "object" && clipData) {
        hasPlainText = typeof clipData.text === "string" && clipData.text;
        hasOtherTypes = (
          (typeof clipData.html === "string" && clipData.html) ||
          (typeof clipData.rtf  === "string" && clipData.rtf )
        );
      }
      return !hasOtherTypes && hasPlainText;
    }
  }
}