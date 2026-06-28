from ethiopian_date import EthiopianDateConverter


ethiopian_date=EthiopianDateConverter.to_ethiopian(2024,9,11)
gc=EthiopianDateConverter.to_gregorian(2016,13,5)

#example of usage
print("Ethiopian",ethiopian_date)
print("GC",gc)