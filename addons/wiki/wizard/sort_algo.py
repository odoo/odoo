def sort(data, index):
    for i in range(len(data)):
        j = i + 1
        for j in range(len(data)-1):
            d1 = data[i].split('.')
            d2 = data[j].split('.')
            
            l1 = len(d1)
            l2 = len(d2)
            max = 0
            if l1 < l2:
                max = l1
            elif l2 < l1:
                max = l2
            else:
                max = l1
            
            if max == 1:
                if int(d1[0]) == int(d2[0]):
                    if len(d1) < len(d2):
                        tmp = data[i]
                        data[i] = data[j]
                        data[j] = tmp
                        continue

            for p in range(0, max):
                val1 = val2 = 0
                try:
                    val1 = int(d1[p])
                except:
                    val1 = 0
                    
                try:
                    val2 = int(d2[p])
                except:
                    val2 = 0
                    
                if val1 < val2:
                    tmp = data[i]
                    data[i] = data[j]
                    data[j] = tmp
            if data[i].startswith(data[j]):
                tmp = data[i]
                tmp = tmp.replace(data[j],'')

def group(data):
    gp = {}
    for i in range(len(data)):
        d1 = data[i].split('.')[0]
        if gp.has_key(d1):
            gp[d1].append(data[i])
        else:
            gp[d1] = [data[i]]
    return gp

def max(data):
    max = 0
    for i in range(len(data)):
        d = str(data[i]).split('.')
        if len(d) > max:
            max = len(d)
            
    return max

def toint(data):
    for i in range(len(data)):
        data[i] = int(data[i])
        
def rearrange(key, groups):
    i = 1
    new = {}
    for ky in key:
        new[i] = groups[str(ky)]
        i += 1
    return new

def reindex(key, groups):
    if groups[0] != key:
        groups[0] = key
    
    lvl_group = {}
    level = max(groups)
    for i in range(len(groups)):
        dg = str(groups[i]).split('.')
        index = len(dg)
        if lvl_group.has_key(str(index)):
            lvl_group[str(index)].append(groups[i])
        else:
            lvl_group[str(index)] = [groups[i]]
    
    for i in range(2, level+1):
        ixd = 1
        gps = lvl_group[str(i)]
        for j in range(len(gps)):
            dt = gps[j].split('.')
            new =""
            for k in range(i-1):
                new += str(dt[k])
                new += '.'
                
            new += str(ixd)
            ixd += 1
            gps[j] = new
            
    print lvl_group
    
if __name__ == '__main__':
    
    data = ['1', '10.1', '10.3', '1.1', '1.2.3', '1.7', '3.1.8', '1.2.2', '1.2.10', '1.3', '1.4', '2', '20.2', '2.1', '2.2', '3', '3.1', '1.2.1', '2.1.2']
    
    sort(data, 0)
    
    grp = group(data)
    
    for gp in grp:
        loop = max(grp[gp])
        for lp in range(1, loop):
            sort(grp[gp],lp)
    
    key = grp.keys()
    toint(key)
    key.sort()
    
    groups = rearrange(key, grp)
    
    new_data = []
    for key in groups:
        new_data.extend(groups[key])
        #print groups[key]
    
    print 'XXXXXXXXXXXXXXXXX : ', new_data
#    print groups
#    
