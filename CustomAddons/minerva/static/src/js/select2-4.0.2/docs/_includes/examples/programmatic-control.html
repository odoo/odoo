<section>
  <h1 id="programmatic-control" class="page-header">
    Programmatic control
  </h1>

  <h2 id="events">DOM events</h2>

  <p>
    Select2 will trigger some events on the original select element,
    allowing you to integrate it with other components. You can find more
    information on events
    <a href="options.html#events">on the options page</a>.
  </p>

  <p>
    <code>change</code> is fired whenever an option is selected or removed.
  </p>

  <p>
    <code>select2:open</code> is fired whenever the dropdown is opened.
    <code>select2:opening</code> is fired before this and can be prevented.
  </p>

  <p>
    <code>select2:close</code> is fired whenever the dropdown is closed.
    <code>select2:closing</code> is fired before this and can be prevented.
  </p>

  <p>
    <code>select2:select</code> is fired whenever a result is selected.
    <code>select2:selecting</code> is fired before this and can be prevented.
  </p>

  <p>
    <code>select2:unselect</code> is fired whenever a result is unselected.
    <code>select2:unselecting</code> is fired before this and can be prevented.
  </p>

  <div class="s2-example">
    <p>
      <select class="js-states js-example-events form-control"></select>
    </p>
    <p>
      <select class="js-states js-example-events form-control" multiple="multiple"></select>
    </p>
  </div>

  <div class="s2-event-log">
    <ul class="js-event-log"></ul>
  </div>

  <pre data-fill-from=".js-code-events"></pre>

<script type="text/javascript" class="js-code-events">
var $eventLog = $(".js-event-log");
var $eventSelect = $(".js-example-events");

$eventSelect.on("select2:open", function (e) { log("select2:open", e); });
$eventSelect.on("select2:close", function (e) { log("select2:close", e); });
$eventSelect.on("select2:select", function (e) { log("select2:select", e); });
$eventSelect.on("select2:unselect", function (e) { log("select2:unselect", e); });

$eventSelect.on("change", function (e) { log("change"); });

function log (name, evt) {
  if (!evt) {
    var args = "{}";
  } else {
    var args = JSON.stringify(evt.params, function (key, value) {
      if (value && value.nodeName) return "[DOM node]";
      if (value instanceof $.Event) return "[$.Event]";
      return value;
    });
  }
  var $e = $("<li>" + name + " -> " + args + "</li>");
  $eventLog.append($e);
  $e.animate({ opacity: 1 }, 10000, 'linear', function () {
    $e.animate({ opacity: 0 }, 2000, 'linear', function () {
      $e.remove();
    });
  });
}
</script>

  <h2 id="programmatic">Programmatic access</h2>

  <p>
    Select2 supports methods that allow programmatic control of the
    component.
  </p>

  <div class="s2-example">

    <p>
      <select class="js-example-programmatic js-states form-control"></select>
    </p>

    <div class="btn-toolbar" role="toolbar" aria-label="Programmatic control">
      <div class="btn-group btn-group-sm" aria-label="Set Select2 option">
        <button class="js-programmatic-set-val btn btn-default">
          Set "California"
        </button>
      </div>
      <div class="btn-group btn-group-sm" role="group" aria-label="Open and close">
        <button class="js-programmatic-open btn btn-default">
          Open
        </button>
        <button class="js-programmatic-close btn btn-default">
          Close
        </button>
      </div>
      <div class="btn-group btn-group-sm" role="group" aria-label="Initialize and destroy">
        <button class="js-programmatic-init btn btn-default">
          Init
        </button>
        <button class="js-programmatic-destroy btn btn-default">
          Destroy
        </button>
      </div>
    </div>

    <p>
      <select class="js-example-programmatic-multi js-states form-control" multiple="multiple"></select>
    </p>

    <div class="btn-group btn-group-sm" role="group" aria-label="Programmatic setting and clearing Select2 options">
      <button type="button" class="js-programmatic-multi-set-val btn btn-default">
        Set to California and Alabama
      </button>
      <button type="button" class="js-programmatic-multi-clear btn btn-default">
        Clear
      </button>
    </div>

  </div>

  <pre data-fill-from=".js-code-programmatic"></pre>

<script type="text/javascript" class="js-code-programmatic">
var $example = $(".js-example-programmatic").select2();
var $exampleMulti = $(".js-example-programmatic-multi").select2();

$(".js-programmatic-set-val").on("click", function () { $example.val("CA").trigger("change"); });

$(".js-programmatic-open").on("click", function () { $example.select2("open"); });
$(".js-programmatic-close").on("click", function () { $example.select2("close"); });

$(".js-programmatic-init").on("click", function () { $example.select2(); });
$(".js-programmatic-destroy").on("click", function () { $example.select2("destroy"); });

$(".js-programmatic-multi-set-val").on("click", function () { $exampleMulti.val(["CA", "AL"]).trigger("change"); });
$(".js-programmatic-multi-clear").on("click", function () { $exampleMulti.val(null).trigger("change"); });
</script>

</section>
