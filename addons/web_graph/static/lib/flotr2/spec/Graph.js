describe('Graph', function () {

  describe('Options', function () {
    var
      nodeA, nodeB,
      a, b, x, i,
      d1 = [],
      options = {};

      for (i = 0; i < 100; i++) {
        x = (i*1000*3600*24*36.5);
        d1.push([x, i+Math.random()*30+Math.sin(i/20+Math.random()*2)*20+Math.sin(i/10+Math.random())*10]);
      }

      options = {
        xaxis : {
          mode : 'time',
          labelsAngle : 45
        },
        selection : {
          mode : 'x'
        },
        HtmlText : false,
      };

    beforeEach(function () {
      nodeA = buildNode();
      Flotr = TestFlotr;
    });

    afterEach(function () {
      destroyNode(nodeA);
      a = b = null;
      Flotr = null;
    });

    it('should override nested default options with user options', function() {
      a = new TestFlotr.Graph(nodeA, d1, options);
      expect(a.options.xaxis.mode).toEqual(options.xaxis.mode);
    });
    
    it('should retain default options if user option\'s nested object does not define property', function() {
      a = new TestFlotr.Graph(nodeA, d1, options);
      expect(a.options.xaxis.tickFormatter).toBeTruthy();
    });

    it('should not affect default options when modifying graph options (objects)', function() {
      a = new TestFlotr.Graph(nodeA, d1, options);
      a.options.x2axis = {  
        titleAlign : 'left'
      };
      a.options.xaxis.scaling = 'logarithmic';
      expect(TestFlotr.defaultOptions.xaxis.scaling).toEqual('linear');
      expect(TestFlotr.defaultOptions.x2axis.titleAlign).toBeFalsy();
    });
    
    /*
    it('should not affect default options when modifying graph options (arrays)', function() {
      a = new TestFlotr.Graph(nodeA, d1, options);
      a.options.colors[1] = '#bada55';
      expect(TestFlotr.defaultOptions.colors[1]).toNotBe('#bada55');
    });
    */

  });

  function buildNode () {
    var node = document.createElement('div');
    document.body.appendChild(node);
    node.style.width = '320px';
    node.style.height = '240px';
    return node;
  }

  function destroyNode (node) {
    document.body.removeChild(node);
  }

});
