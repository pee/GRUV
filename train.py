from __future__ import absolute_import
from __future__ import print_function
import numpy as np
import os
import nn_utils.network_utils as network_utils
import config.nn_config as nn_config
import tensorflow as tf
import argparse

parser = argparse.ArgumentParser(description="Train the GRUV network against the current dataset.")
parser.add_argument("current_iteration", default=0, type=int, help="Current training iteration to start from.")
parser.add_argument("num_iterations", default=50, type=int, help="Total number of iterations to perform.")
parser.add_argument("-e", "--epochs", default=25, type=int, help="Number of epochs per iteration.")
parser.add_argument("-b", "--batch", default=None, type=int, help="Number of training examples per gradient update. Defaults to None which will attempt to load all examples in one batch.")
parser.add_argument("-v", "--validation", default=True, type=bool, help="Use cross validation data.")
args = parser.parse_args()

sess = tf.Session(config=tf.ConfigProto(log_device_placement=True))

config = nn_config.get_neural_net_configuration()
inputFile = config['model_file']
cur_iter = args.current_iteration
model_basename = config['model_basename']
model_filename = model_basename + str(cur_iter)
use_validation = args.validation

#Load up the training data
print ('Loading training data')
#X_train is a tensor of size (num_train_examples, num_timesteps, num_frequency_dims)
#y_train is a tensor of size (num_train_examples, num_timesteps, num_frequency_dims)
X_train = np.load(inputFile + '_x.npy')
y_train = np.load(inputFile + '_y.npy')
if use_validation:
    X_val = np.load(inputFile + '_val_x.npy')
    y_val = np.load(inputFile + '_val_y.npy')
print ('Finished loading training data')

#Figure out how many frequencies we have in the data
num_timesteps = X_train.shape[1]
freq_space_dims = X_train.shape[2]
hidden_dims = config['hidden_dimension_size']
recurrent_units = config['hidden_recurrent_layers']

#Creates a lstm network
print('Initializing network...')
model = network_utils.create_lstm_network(num_frequency_dimensions=freq_space_dims, num_hidden_dimensions=hidden_dims, num_recurrent_units=recurrent_units)
#You could also substitute this with a RNN or GRU
#model = network_utils.create_gru_network()

#Load existing weights if available
if os.path.isfile(model_filename):
    print ('Loading existing weight data from {}'.format(model_filename))
    model.load_weights(model_filename)

num_iters = cur_iter + args.num_iterations 		#Number of iterations for training
epochs_per_iter = args.epochs	                #Number of iterations before we save our model
if args.batch == None:                          #Number of training examples per gradient update
    batch_size = X_train.shape[0]
else:
    batch_size = args.batch

#def prepare_validation_split(x_train, y_train, x_val, y_val, validate_size):
    #if validate_size == 0:
        #return x_train, y_train, x_val, y_val
    #sample_max = x_train.shape[0] - validate_size
    #stride = x_train.shape[0] / validate_size
    #for i in xrange(0, sample_max, stride):
        #x_val = np.concatenate((x_val, np.reshape(x_train[i], (1, x_train.shape[1], x_train.shape[2]))), axis=0)
        #y_val = np.concatenate((y_val, np.reshape(y_train[i], (1, y_train.shape[1], y_train.shape[2]))), axis=0)
        #x_train = np.delete(x_train, i, axis=0)
        #y_train = np.delete(y_train, i, axis=0)
    #return x_train, y_train, x_val, y_val

## Set up validation split
#validate_size = int(round(X_train.shape[0] * validation_split))
#assert X_train.shape[0] == y_train.shape[0]
#X_val = np.zeros((0, X_train.shape[1], X_train.shape[2]))
#y_val = np.zeros((0, y_train.shape[1], y_train.shape[2]))
#print('Splitting data for validation...')
#data_parts = prepare_validation_split(X_train, y_train, X_val, y_val, validate_size)
#X_train = data_parts[0]
#y_train = data_parts[1]
#X_val = data_parts[2]
#y_val = data_parts[3]

print('Training set shape: {0}'.format(X_train.shape))
if use_validation:
    print('Validation set shape: {0}'.format(X_val.shape))

print ('Starting training!')
while cur_iter < num_iters:
    print('Iteration: ' + str(cur_iter))
    history = model.fit(X_train, y_train, batch_size=batch_size, epochs=epochs_per_iter, shuffle=True, verbose=1, validation_split=0.0).history
    save_metrics = {'train_losses' : history['loss']}
    
    if use_validation:
        val_loss = model.evaluate(X_val, y_val, verbose=1)
        save_metrics = {'val_loss' : val_loss}
        print('validation loss: %f' % val_loss)
    
    if cur_iter % (epochs_per_iter * 5) != 0 and os.path.isfile(model_basename + str(cur_iter)):
        os.remove(model_basename + str(cur_iter))
        
    cur_iter += epochs_per_iter
    
    print ('Saving weights for iteration {0} ...'.format(cur_iter))
    model.save_weights(model_basename + str(cur_iter))
    np.save('loss_metrics_iteration-%d.npy' % cur_iter, save_metrics)
    
print ('Training complete!')
