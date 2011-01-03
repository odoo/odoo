This module provide a generic framework to define your own quality test. 


All you have to do is to:
* create a folder with your test in 'base_module_quality' (e.g: mkdir base_module_quality\mytest)
* create a .py file in it with same name as the folder you just created (e.g: touch base_module_quality\mytest\mytest.py)
* edit your file and define a class 'quality_check' that 
    * inherits the class 'abstract_quality_test' (defined in base_module_quality.py) 
    * implements the __init__() method accordingly to what you want to test.


