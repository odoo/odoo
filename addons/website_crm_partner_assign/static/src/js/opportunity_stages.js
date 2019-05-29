document.addEventListener('DOMContentLoaded', function(){
    var stages = document.getElementById('stages');
    if(stages.offsetWidth < 440){
        stages.className ="col-md text-md-right"
        console.log("shifted right!")
    }
    else{
    	console.log("stay to the left")
    }
})