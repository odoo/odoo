module.exports = {
    printUsage: function() {
        console.log("");
        console.log("Clean CSS Plugin");
        console.log("specify plugin with --clean-css");
        console.log("To pass an option to clean css, we use similar CLI arguments as from https://github.com/GoalSmashers/clean-css");
        console.log("The exception is advanced and rebase - we turn these off by default so use advanced/rebase to turn it back on again.");
        console.log("--clean-css=\"-s1 --advanced --rebase\"");
        console.log("The options do not require dashes, so this is also equivalent");
        console.log("--clean-css=\"s1 advanced rebase\"");
        this.printOptions();
        console.log("");
    },
    printOptions: function() {
        console.log("we support the following arguments... 'keep-line-breaks', 'b'");
        console.log("'s0', 's1', 'advanced', 'rebase', 'keepSpecialComments', compatibility', 'rounding-precision'");
        console.log("'skip-aggressive-merging', 'skip-shorthand-compacting'")
    }
};
