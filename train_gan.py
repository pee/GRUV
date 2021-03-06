from __future__ import absolute_import
from __future__ import print_function
from generate import generate
import numpy as np
import os
import nn_utils.network_utils as network_utils
import config.nn_config as nn_config
import gen_utils.seed_generator as seed_generator
import gen_utils.sequence_generator as sequence_generator
import tensorflow as tf
import argparse

# Default maximum batch size for 'auto' batching
MAX_DECODER_EXAMPLES = 100

config = nn_config.get_neural_net_configuration()

parser = argparse.ArgumentParser(description="Train the NuGRUV GAN against the current dataset.")
parser.add_argument("current_iteration", default=0, type=int, help="Current training iteration to start from.")
parser.add_argument("num_iterations", default=10, type=int, help='Number of training iterations to run.')
parser.add_argument("--dec-epochs", default=50, type=int, help="Number of epochs per iteration to train the decoder.")
parser.add_argument("--gen-epochs", default=25, type=int, help="Number of epochs per iteration of the generator.")
parser.add_argument("--com-epochs", default=1, type=int, help="Number of epochs per iteration to train the combined GAN model.")
parser.add_argument("--dec-samples", default=10, type=int, help="Number of decoder samples to use.")
parser.add_argument("-b", "--max-batch", default=500, type=int, help="Maximum number of training examples to batch per gradient update.")
parser.add_argument("--skip-validation", action="store_true", help="Do not use cross validation data.")
parser.add_argument("-n", "--interval", default=10, type=int, help="Number of iterations to run in between retaining saved weights.")
parser.add_argument("-o", "--optimizer", default="rmsprop", type=str, help="Name of the optimizer to use for the generative model. Defaults to 'rmsprop'")
parser.add_argument("-d", "--dropout", default=0.3, type=float, help="Probability of dropout applied to the first layer of the generative network.")
parser.add_argument("-r", "--run", default=0, type=int, help="Integer id for this run (used for weight files). Defaults to zero.")
parser.add_argument("--hidden-dims", default=config['hidden_dimension_size'], type=int, help="Number of hidden layer dimensions.")
args = parser.parse_args()

sess = tf.Session(config=tf.ConfigProto(log_device_placement=True))

inputFile = config['model_file']
cur_iter = args.current_iteration
dec_basename = config['model_basename'] + str(args.run) + '-Dec_'
dec_filename = dec_basename + str(cur_iter)
gen_basename = config['model_basename'] + str(args.run) + '_'
gen_filename = gen_basename + str(cur_iter)
skip_validation = args.skip_validation

#Load up the training data
print('Loading training data')
#X_train is a tensor of size (num_train_examples, num_timesteps, num_frequency_dims)
#y_train is a tensor of size (num_train_examples, num_timesteps, num_frequency_dims)
X_train = np.load(inputFile + '_x.npy')
y_train = np.load(inputFile + '_y.npy')
print(X_train.shape)
print(y_train.shape)
if not skip_validation:
    X_val = np.load(inputFile + '_val_x.npy')
    y_val = np.load(inputFile + '_val_y.npy')
    print(X_val.shape)
    print(y_val.shape)
print('Finished loading training data')

#Figure out how many frequencies we have in the data
num_timesteps = X_train.shape[1]
freq_space_dims = X_train.shape[2]
hidden_dims = args.hidden_dims

#Creates a Genearative Adverserial Network (GAN) using the normal NuGRUV LSTM network as the generator.
print('Initializing network...')
gan = network_utils.create_gan(num_frequency_dimensions=freq_space_dims, num_hidden_dimensions=hidden_dims, optimizer=args.optimizer, dropout_rate=args.dropout)

print('Model summary:')
gan.summary()

#Load existing weights if available
if os.path.isfile(dec_filename):
    print('Loading existing weight data (Decoder) from {}'.format(dec_filename))
    gan.decoder.load_weights(dec_filename)
if os.path.isfile(gen_filename):
    print('Loading existing weight data (Generator) from {}'.format(gen_filename))
    gan.generator.load_weights(gen_filename)

batch_size = X_train.shape[0]
while batch_size > args.max_batch:
    batch_size = int(np.ceil(batch_size / 2.0))

# Deprecated, dynamic validation splitting. Incurs a lot of additional computational overhead per training recurrent_units
# ...
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
val_data = None
if not skip_validation:
    print('Validation set shape: {0}'.format(X_val.shape))
    val_data = (X_val, y_val)

def random_training_examples(X_train, seed_len=1, count=1):
    examples = np.zeros((0,X_train.shape[1]*seed_len,X_train.shape[2]))
    for i in xrange(count):
        next_example = seed_generator.generate_copy_seed_sequence(seed_length=seed_len, training_data=X_train)
        examples = np.concatenate((examples, next_example), axis=0)
    return examples

def train_decoder(X_train, sample_size):
    print('Training decoder...')
    X_real = random_training_examples(X_train, seed_len=1, count=sample_size)
    print(X_real.shape)
    # Generate fake examples from random seeds. To make sure we train the decoder on the same input it will receive from the generator
    # in the combined model, we need to cap the sequence length at 'num_timesteps' (note: this means only the model's reproduction of the seed sequence + 1 num_timesteps
    # will be included in the output; room for further improvement)
    X_fake = generate(gan.generator, X_train, max_seq_len=num_timesteps, gen_count=sample_size, include_raw_seed=False, include_model_seed=True, uncenter_data=False)
    print(X_fake.shape)
    dec_hist = gan.fit_decoder(X_real, X_fake, epochs=args.dec_epochs, shuffle=True, verbose=1, validation_split=0.25)
    
# Training phase 1: Generator pre-training
print('Starting training...')
decoder_data_len = min(args.dec_samples, min(MAX_DECODER_EXAMPLES, X_train.shape[0]))
# If we're not starting at zero, then bump current iteration up one, assuming we've loaded weights for the starting iteration
if cur_iter > 0:
    cur_iter += 1
num_iters = cur_iter + args.num_iterations
while cur_iter < num_iters:
    # Start training iteration for each model
    print('Iteration: {0}'.format(cur_iter))
    print('Training generator for {0} epochs (batch size: {1})'.format(args.gen_epochs, batch_size))
    gen_hist = gan.fit_generator(X_train, y_train, batch_size=batch_size, epochs=args.gen_epochs, shuffle=True, verbose=1, validation_data=val_data)
    print('Saving generator weights (pre-train) for iteration {0} ...'.format(cur_iter))
    gan.generator.save_weights(gen_basename + str(cur_iter))
    print('Training decoder for {0} epochs with {1} training examples'.format(args.dec_epochs, decoder_data_len))
    dec_hist = train_decoder(X_train, decoder_data_len)
    print('Saving decoder weights for iteration {0} ...'.format(cur_iter))
    gan.decoder.save_weights(dec_basename + str(cur_iter))
    print('Training combined model for {0} epochs'.format(args.com_epochs))
    gan.fit(X_train, batch_size=batch_size, epochs=args.com_epochs, shuffle=True, verbose=1, validation_split=0.25)
    print('Saving generator weights (post-train) for iteration {0} ...'.format(cur_iter))
    gan.generator.save_weights(gen_basename + str(cur_iter))
    
    # Clean weights from last iteration, if between persistent save intervals
    last_iter = cur_iter - 1
    if last_iter >= 0 and last_iter % args.interval != 0:
        if os.path.isfile(gen_basename + str(last_iter)):
            os.remove(gen_basename + str(last_iter))
        if os.path.isfile(dec_basename + str(last_iter)):
            os.remove(dec_basename + str(last_iter))
            
    cur_iter += 1
    
print('Training complete!')

