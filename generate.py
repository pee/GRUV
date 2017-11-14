from __future__ import absolute_import
from __future__ import print_function
import numpy as np
import os
import nn_utils.network_utils as network_utils
import gen_utils.seed_generator as seed_generator
import gen_utils.sequence_generator as sequence_generator
from data_utils.parse_files import *
import config.nn_config as nn_config
import argparse

def generate(model, X_train, max_seq_len, seed_len=1, gen_count=1, include_seed_in_output=True, uncenter_data=False, X_var=None, X_mean=None):
    print ('Starting generation!')
    #Here's the interesting part
    #We need to create some seed sequence for the algorithm to start with
    #Currently, we just grab an existing seed sequence from our training data and use that
    #However, this will generally produce verbatum copies of the original songs
    #In a sense, choosing good seed sequences = how you get interesting compositions
    #There are many, many ways we can pick these seed sequences such as taking linear combinations of certain songs
    #We could even provide a uniformly random sequence, but that is highly unlikely to produce good results
    outputs = []
    for i in range(gen_count):
        print("Generating sample {0}/{1}".format(i+1, gen_count))
        seed_seq = seed_generator.generate_copy_seed_sequence(seed_length=seed_len, training_data=X_train)
        output = sequence_generator.generate_from_seed(model, seed_seq, max_seq_len, include_seed_in_output, uncenter_data, X_var, X_mean)
        outputs.append(output)
    return np.array(outputs)
    print('Finished generation!')
    
def __main__():
    config = nn_config.get_neural_net_configuration()
    parser = argparse.ArgumentParser(description="Generate song from current saved training data.")
    parser.add_argument("--batch", default=1, type=int, help="Number of generations to run.")
    parser.add_argument("--iteration", default=0, type=int, help="Current training iteration load weights for.")
    parser.add_argument("--seqlen", default=10, type=int, help="Sequence length.")
    parser.add_argument("--use-train", action='store_true', help='True if training data should be sampled to seed generation. Defaults to false (use generation data).')
    parser.add_argument("--include-seed", action='store_true', help="True if the generated audio should include the model's prediction output for the seed samples.")
    parser.add_argument("--hidden-dims", default=config['hidden_dimension_size'], type=int, help="Number of hidden layer dimensions.")
    parser.add_argument("--hidden-layers", default=config['hidden_recurrent_layers'], type=int, help="Number of hidden layers (generator only).")
    args = parser.parse_args()

    sample_frequency = config['sampling_frequency']
    if args.use_train:
        inputFile = config['model_file']
    else:
        inputFile = config['gen_file']
    model_basename = config['model_basename']
    cur_iter = args.iteration
    gen_count = args.batch
    model_filename = model_basename + str(cur_iter)
    output_filename = './generated_song'

    #Load up the training data
    if args.use_train:
        print('Loading training data')
    else:
        print('Loading generation data')
    #X_train is a tensor of size (num_train_examples, num_timesteps, num_frequency_dims)
    #y_train is a tensor of size (num_train_examples, num_timesteps, num_frequency_dims)
    #X_mean is a matrix of size (num_frequency_dims,) containing the mean for each frequency dimension
    #X_var is a matrix of size (num_frequency_dims,) containing the variance for each frequency dimension
    X_train = np.load(inputFile + '_x.npy')
    y_train = np.load(inputFile + '_y.npy')
    X_mean = np.load(inputFile + '_mean.npy')
    X_var = np.load(inputFile + '_var.npy')
    print('Finished loading data')

    #Figure out how many frequencies we have in the data
    num_timesteps = X_train.shape[1]
    freq_space_dims = X_train.shape[2]
    hidden_dims = args.hidden_dims
    hidden_layers = args.hidden_layers

    #Creates a lstm network
    print('Initializing network...')
    model = network_utils.create_lstm_network(num_frequency_dimensions=freq_space_dims, num_hidden_dimensions=hidden_dims, num_recurrent_units=hidden_layers)
    #model = network_utils.create_noise_network(num_frequency_dimensions=freq_space_dims, num_hidden_dimensions=hidden_dims)
    #You could also substitute this with a RNN or GRU
    #model = network_utils.create_gru_network()

    print('Model summary:')
    model.summary()

    #Load existing weights if available
    if os.path.isfile(model_filename):
        print('Loading weights from file {0}'.format(model_filename))
        model.load_weights(model_filename)
    else:
        print('Model filename ' + model_filename + ' could not be found!')

    max_seq_len = args.seqlen; #Defines how long the final song is. Total song length in samples = max_seq_len * example_len

    outputs = generate(model, X_train, max_seq_len, gen_count=gen_count, include_seed_in_output=args.include_seed, uncenter_data=True, X_var=X_var, X_mean=X_mean)
    for i in xrange(gen_count):
        #Save the generated sequence to a WAV file
        save_generated_example('{0}_{1}.wav'.format(output_filename, i), outputs[i], sample_frequency=sample_frequency)
        
if __name__ == '__main__':
    __main__()
