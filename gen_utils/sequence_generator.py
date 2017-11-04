import numpy as np

#Extrapolates from a given seed sequence
def generate_from_seed(model, seed, sequence_length, data_variance, data_mean):
    seedSeq = seed.copy()
    output = []
    #for i in xrange(seedSeq.shape[1]):
        #output.append(seedSeq[0][i])

    #The generation algorithm is simple:
    #Step 1 - Given A = [X_0, X_1, ... X_n], generate X_n + 1
    #Step 2 - Concatenate X_n + 1 onto A
    #Step 3 - Repeat MAX_SEQ_LEN times
    for it in xrange(sequence_length):
        seedSeqNew = model.predict(seedSeq) #Step 1. Generate X_n + 1
        #Step 2. Append it to the sequence
        if it == 0:
            for i in xrange(seedSeqNew.shape[1]):
                output.append(seedSeqNew[0][i].copy())
        else:
            output.append(seedSeqNew[0][seedSeqNew.shape[1]-1].copy()) 
        newSeq = seedSeqNew[0][seedSeqNew.shape[1]-1]
        newSeq = np.reshape(newSeq, (1, 1, newSeq.shape[0]))
        seedSeq = np.concatenate((seedSeq, newSeq), axis=1)
        #print(seedSeq.shape)
        seedSeq = seedSeq[:,1:,:]
        #print(seedSeq.shape)

    ##Finally, post-process the generated sequence so that we have valid frequencies
    ##We're essentially just undo-ing the data centering process
    for i in xrange(len(output)):
        output[i] *= data_variance
        output[i] += data_mean
    return output
    
    
    
    
    #print(seedSeq.shape)
    #for it in xrange(sequence_length):
        #seedSeqNew = model.predict(seedSeq) #Step 1. Generate X_n + 1
        ##Step 2. Append it to the sequence
        #for i in xrange(seedSeqNew.shape[1]):
            #output.append(seedSeqNew[-1][i].copy())
        ##newSeq = seedSeqNew[0][seedSeqNew.shape[1]-1]
        ##newSeq = np.reshape(newSeq, (1, 1, newSeq.shape[0]))
        #newSeq = seedSeqNew[-1][np.newaxis,:]
        ##seedSeq = np.concatenate((seedSeq, newSeq), axis=0)
        #seedSeq = newSeq
        #print(seedSeq.shape)

    ##Finally, post-process the generated sequence so that we have valid frequencies
    ##We're essentially just undo-ing the data centering process
    #for i in xrange(len(output)):
        #output[i] *= data_variance
        #output[i] += data_mean
    #return output
