import json
import random
import re
import string
from typing import List

#learn python
class Person:
    name: str
    age: int

    def __init__(self, name=None, age=None):
        self.name = name
        self.age = age

    def __str__(self):
        return f"{self.name}({self.age})"

    
class Student(Person):
    stt: int
    score: float
    
    def toStringValue(self):
        mystr = self.name + ' - ' + str(self.age) + ' - ' + str(self.score) + ' - ' + str(self.stt)
        return mystr


class Class:
    total: int
    students = []
    grade: int
    rank: int
    name: str

    def randomList(self):
        if(self.total is not None):
            for i in range(self.total):
                stu = Student()
                stu.name = 'student' + str(i)
                stu.age = 18
                stu.score = random.randint(1, 10)
                stu.stt = i
                self.students.append(stu)

    def searchByName(self, keyword):
            data = []
            for i in range(self.total):
                if(keyword  in self.students[i].name):
                    data.append(self.students[i])
                    # print(self.students[i])
            
    def statisticalByScore(self, targetScore): 
            data = []
            for i in range(self.total):
                if(self.students[i].score > targetScore):
                    data.append(self.students[i])
                    print(self.students[i].name)
                    print(self.students[i].score)
                    print('=====================')

    def insertStudent(self, name: string, age:int, score:float):
            temp = Student()
            temp.name = name
            temp.age = age
            temp.score = score
            temp.stt = self.total + 1
            self.total += 1
            try:
                self.students.append(temp)
                print('insert success')
                print('total: ' + str(self.total))
            except:
                print('insert err')

    def deleteStudent(self, uid:int):
           
            try:
                for i in range(self.total):
                    if(uid == i):
                        self.students.pop(id)
                        self.total -= 1
                        print('delete success')
                        print('total: ' + str(self.total))                        
            except:
                print('delete err')

    def updateStudent(self, uid:int, name=None, age=None, score=None):
           
            try:
                for i in range(self.total):
                    if(uid == i):
                        print('before update')
                        print(self.students[i].__dict__)
                        if name:
                            self.students[i].name = name
                        if age:
                            self.students[i].age = age
                        if score:
                            self.students[i].score = score
                        print('after update')
                        print(self.students[i].__dict__)
            except:
                print('delete err')
                
    def sortStudentByScore(self):
            self.students.sort(key=lambda x: x.score)
            for i in range(self.total):
                print(self.students[i].__dict__)

    #
    def groupByScore(self):
            gioi = []  # score >=8
            kha = []  #  >=6.5 score <8
            trungBinh = []  # 4<= score <6.5
            yeu = []  # score<4
            for i in range(self.total):
                stu: Student
                stu = self.students[i]
                if(stu.score >= 8):
                    gioi.append(stu)
                elif stu.score >= 6.5:
                    kha.append(stu)
                elif stu.score >= 4:
                    trungBinh.append(stu)
                else:
                    yeu.append(stu)

    def saveDocument(self):
        try:
            f = open("dataStudents.txt", "w")
            content = ''
            for i in self.students:
                content += ' \n ' + json.dumps(i.__dict__)              
            f.write(content)
            print('save success')
            f.close()
        except:
            print('can not save the file')

    def readDocument(self):
        try:
            f = open("dataStudents.txt", "r")
            content = f.read()
            print(content)
            
            f.close()
        except:
            print('can not read the file')
        

ranks = ('A', 'B', 'C')

    
class school:
    name: str
    type: int
    total: int
    rankID: int
    classList: []

    def randomList(self):

            def randomList(self):
                if(self.total is not None):
                    for i in range(self.total):
                        __class = Class()
                        __class.name = str(ranks[self.rankID]) + str(i)
                        __class.total = random.randint(25, 40)
                        __class.stt = i
                        self.classList.append(__class)

    
myclass = Class()
myclass.total = 20
myclass.randomList()
# myclass.updateStudent(1,'duy')
# myclass.sortStudentByScore()
myclass.saveDocument()

myclass.readDocument()
# print(myclass.students[0].__dict__)

# try:
#     myclass.insertStudent('quyen', 18, 9)
#     myclass.deleteStudent(2)
# except NameError as e:
#     print(e)
# print(myclass.students[1].score)
myclass.searchByName('1')
# try:
#     myclass.statisticalByScore(8)
# except NameError as e:
#     print(e)


#
def twoSum(nums: List[int], target: int) -> List[int]:
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                if nums[j] == target - nums[i]:
                    return [i, j]


def isPalindrome(s: str) -> bool:
        s = re.sub('[^A-Za-z0-9]+', '', s)
        if(s.lower() == s[::-1].lower()):
            return True
        else:
            return False
        
# Given an array of integers nums which is sorted in ascending order, and an integer target, write a function to search target in nums. If target exists, then return its index. Otherwise, return -1.


# You must write an algorithm with O(log n) runtime complexity.        
def search(nums: List[int], target: int) -> int:
        for i in range(len(nums)):
            if target == nums[i]:
                return i
        return -1


# Given an integer array nums, move all 0's to the end of it while maintaining the relative order of the non-zero elements.    
def moveZeroes(nums: List[int]) -> None:
        count = nums.count(0)        
        for i in range(count):
            nums.remove(0)
            nums.append(0)

# Given an array nums containing n distinct numbers in the range [0, n], return the only number in the range that is missing from the array.

           
def missingNumber(nums: List[int]) -> int:
        mymax = max(nums)
        if(len(nums) - 1 == mymax):
            return mymax + 1
        else:
            for i in range(mymax):
                if i not in nums:
                    return i
        return 0


def isPalindromeNum(x: int) -> bool:
        temp = str(x)
        if(temp == temp[::-1]):
            return True
        return False 


# Given an integer array nums sorted in non-decreasing order, return an array of the squares of each number sorted in non-decreasing order.   
def sortedSquares(nums: List[int]) -> List[int]:
        for i in range(len(nums)):
            nums[i] = nums[i] ** 2
        nums.sort()
        return nums


x = "A man, a plan, a canal: Panama"
print(isPalindrome(x))







