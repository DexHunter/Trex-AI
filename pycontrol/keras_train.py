#!/usr/bin/env python
import tensorflow as tf
from keras_network import DeepQNN
import cv2
import random
import numpy as np
from collections import deque
import sys
sys.path.append("../pygame/")
import wrapped_trex as game

GAME = 'trex' # the name of the game being played for log files
ACTIONS = 2 # number of valid actions
GAMMA = 0.99 # decay rate of past observations
OBSERVE = 30000. # timesteps to observe before training
EXPLORE = 3000000. # frames over which to anneal epsilon
FINAL_EPSILON = 0.0001 # final value of epsilon
INITIAL_EPSILON = 0.1 # starting value of epsilon
REPLAY_MEMORY = 50000 # number of previous transitions to remember
BATCH = 32 # size of minibatch
FRAME_PER_ACTION = 1

def trainNetwork(q_network):
    # open up a game state to communicate with emulator
    game_state = game.GameState()

    # store the previous observations in replay memory
    D = deque()

    # printing
    #a_file = open("./logs/readout.txt", 'w')
    #h_file = open("./logs/hidden.txt", 'w')

    # get the first state by doing nothing and preprocess the image to 80x80x4
    do_nothing = np.zeros(ACTIONS)
    do_nothing[0] = 1
    x_t, r_0, terminal = game_state.frame_step(do_nothing)
    x_t = cv2.cvtColor(cv2.resize(x_t, (80, 80)), cv2.COLOR_BGR2GRAY)
    s_t = np.stack((x_t, x_t, x_t, x_t), axis=0)

    # saving and loading networks
    '''
    saver = tf.train.Saver()
    sess.run(tf.initialize_all_variables())
    checkpoint = tf.train.get_checkpoint_state("saved_networks")
    if checkpoint and checkpoint.model_checkpoint_path:
        saver.restore(sess, checkpoint.model_checkpoint_path)
        print("Successfully loaded:", checkpoint.model_checkpoint_path)
    else:
        print("Could not find old network weights")
    '''

    # start training
    epsilon = INITIAL_EPSILON
    t = 0
    while True:
        # game.update()
        # choose an action epsilon greedily
        #readout_t = readout.eval(feed_dict={s : [s_t]})[0]
        action_result, Q = q_network.TestModel(np.array([s_t]))
        action_index = action_result[0]
        a_t = np.zeros([ACTIONS])
        if t % FRAME_PER_ACTION == 0:
            if random.random() <= epsilon:
                print("----------Random Action----------")
                print action_index
                action_index = random.randrange(ACTIONS)
                a_t[action_index] = 1
                print Q
            else:
                a_t[action_index] = 1
        else:
            a_t[0] = 1 # do nothing

        # scale down epsilon
        if epsilon > FINAL_EPSILON and t > OBSERVE:
            epsilon -= (INITIAL_EPSILON - FINAL_EPSILON) / EXPLORE

        # run the selected action and observe next state and reward
        x_t1_c, r_t, terminal = game_state.frame_step( a_t)
        x_t1 = cv2.cvtColor(cv2.resize(x_t1_c, (80, 80)), cv2.COLOR_BGR2GRAY)
        #x_t1 = np.reshape(x_t1, (80, 80, 1))
        #s_t1 = np.append(x_t1, s_t[:,:,1:], axis = 2)
        if terminal:
            print 'terminal!'
            print 'r_t: ' + str(r_t)
        s_t1 = np.append(np.array([x_t1]), s_t[1:, :, :], axis=0)

        # store the transition in D
        D.append((s_t, action_index, r_t, s_t1, terminal))
        if len(D) > REPLAY_MEMORY:
            D.popleft()

        print 't: ' + str(t)
        # only train if done observing
        if t > OBSERVE:
            # sample a minibatch to train on
            minibatch = random.sample(D, BATCH)

            # get the batch variables
            s_j_batch = np.array([d[0] for d in minibatch])
            a_batch = np.array([d[1] for d in minibatch])
            r_batch = np.array([d[2] for d in minibatch])
            s_j1_batch = np.array([d[3] for d in minibatch])

            y_batch = []
            actionResult_j1, readout_j1_batch = q_network.TestModel(s_j1_batch)
            for i in range(0, len(minibatch)):
                terminal = minibatch[i][4]
                # if terminal, only equals reward
                if terminal:
                    y_batch.append(r_batch[i])
                else:
                    y_batch.append(r_batch[i] + GAMMA * np.max(readout_j1_batch[i]))

            # perform gradient step
            actionResult_j, readout_j_batch = q_network.TestModel(s_j_batch)
            for i in range(0, len(minibatch)):
                readout_j_batch[i][int(a_batch[i])] = y_batch[i]
            q_network.TrainModel(s_j_batch, readout_j_batch)

        # update the old values
        s_t = s_t1
        t += 1

        # save progress every 10000 iterations
        if t % 10000 == 0:
            q_network.model.save('keras_model.h5')
        if t%10000 < 50:
            cv2.imwrite("/Users/yiweizhao/Desktop/SHOW/" + str(t) + ".png", x_t1)

def playGame():
    QNetwork = DeepQNN()
    QNetwork.BuildModel()
    trainNetwork(QNetwork)

def main():
    playGame()

if __name__ == "__main__":
    main()
