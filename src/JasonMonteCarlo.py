import os
import torch
import pickle
from tqdm import tqdm
import logging
import copy
import numpy as np
import datetime
import torch.multiprocessing as mp
from rules.Mancala import Board
from ConnectNet import ConnectNet, Net
from NeuralNet import NeuralNet, TwoLayerNet, JasonNet
from Node import Node

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
logger = logging.getLogger(__file__)


def run_monte_carlo(net, start_ind, iteration, episodes=100):
    if torch.cuda.is_available():
        net.cuda()

    logger.info("Prepare network for multi threaded Tree search")
    mp.set_start_method("spawn", force=True)
    net.share_memory()
    net.eval()

    # Load or save the neural network
    net_name = "net_iter%d.pth.tar" % iteration
    net_filename = os.path.join("./model_data/", net_name)
    if os.path.isfile(net_filename):
        checkpoint = torch.load(net_filename)
        net.load_state_dict(checkpoint)
        logger.info("Loaded %s model." % net_filename)
    else:
        torch.save(net.state_dict(), net_filename)
        logger.info("Saved initial model.")

    # Spawn processes to self play the game
    # TODO pass this in perhaps. Does 32 currently
    processes = []
    num_processes = 1  # mp.cpu_count()

    logger.info("Spawning {} processes".format(num_processes))
    with torch.no_grad():
        for i in range(num_processes):
            p = mp.Process(target=self_play, args=(net, episodes, start_ind, i, 1.1, iteration))
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
    logger.info("Finished multi-process MCTS!")


def self_play(net, episodes, start_ind, cpu, temperature, iteration):
    logger.info("[CPU: %d]: Starting MCTS self-play..." % cpu)

    # Make directory for training iteration
    if not os.path.isdir("./datasets/iter_%d" % iteration):
        if not os.path.isdir("datasets"):
            os.mkdir("datasets")
        os.mkdir("datasets/iter_%d" % iteration)

    # tqdm is a progress bar
    for ind in tqdm(range(start_ind, episodes + start_ind)):
        logger.info("[CPU: %d]: Game %d" % (cpu, ind))
        game = Board()  # new game to play with
        is_game_over = False
        replay_buffer = []  # (state, policy, value) for NN training
        value = 0  # winning player?
        move_count = 0  # number of moves so far in the game

        # While no winner and actions you can do
        while is_game_over is False and \
                game.get_legal_moves() != []:
            #  TODO move to cinfg and add dirichlet noise
            # Choose best policy after 11 moves.
            if move_count < 11:
                t = temperature
            else:
                t = 0.1

            state_copy = copy.deepcopy(game.current_board)

            root = search(game, 777, net)  # TODO put 777 in config
            policy = get_policy(root, t)
            print("[CPU: %d]: Game %d POLICY:\n " % (cpu, ind), policy)

            # current_board = do_decode_n_move_pieces(current_board, \
            #                          np.random.choice(
            #                          np.array([0, 1, 2, 3,4, 5, 6]), \
            #                                       p=policy))
            legal_moves = game.get_legal_moves()
            player_policy = game.get_legal_moves_from_policy(legal_moves
                                                             , policy)
            game.process_move(np.random.choice(legal_moves,
                                               p=player_policy))

            replay_buffer.append([state_copy, policy])
            print("[Iteration: %d CPU: %d]: Game %d CURRENT BOARD:\n" %
                  (iteration, cpu, ind),game.current_board, game.player)
            print(" ")
            if game.game_over() is True:  # if somebody won
                # TODO winner is not so simple. negative for player 2
                #  with absolute value on player 2?
                value = game.player
                is_game_over = True
            move_count += 1
        dataset = []
        # replay_buffer is [board_state, policy]
        for idx, data in enumerate(replay_buffer):
            s, p = data
            if idx == 0:
                dataset.append([s, p, 0])
            else:
                dataset.append([s, p, value])
        del replay_buffer
        save_as_pickle("iter_%d/" % iteration +
                       "dataset_iter%d_cpu%i_%i_%s" % (
                           iteration, cpu, ind, datetime.datetime
                           .today().strftime("%Y-%m-%d")), dataset)


def search(game, sim_nbr, net):
    # Create root node
    root = Node(game, move=None, parent=None)
    logger.info("Search for best action")

    # For number of simulations find a leaf and evaluate the board with
    # the neural network. if the game is one, backup the winning value
    for _ in range(sim_nbr):  # number of simulations
        leaf = root.select_leaf()
        current_board_t = torch.tensor(leaf.game.current_board,
                                       dtype=torch.float32)
        # return a new tensor with a 1 dimension added at provided index
        current_board_t_sqzd = current_board_t.unsqueeze(0).unsqueeze(0)

        # Use neural net to predict policy and value
        policy, estimated_val = net(current_board_t_sqzd)
        child_priors_numpy = policy.detach().cpu().numpy()
        estimated_val = estimated_val.item()

        # Check if game over
        if leaf.game.check_winner() is True:
            leaf.backup(estimated_val)
            continue
        leaf.expand(child_priors_numpy)  # need to make sure valid moves
        leaf.backup(estimated_val)
    return root


def get_policy(root, temp=1):
    return (root.child_number_visits ** (1 / temp)) / \
           sum(root.child_number_visits ** (1 / temp))


def save_as_pickle(filename, data):
    complete_name = os.path.join("./datasets/", filename)
    with open(complete_name, 'wb') as output:
        pickle.dump(data, output)


def load_pickle(filename):
    complete_name = os.path.join("./datasets/", filename)
    with open(complete_name, 'rb') as pkl_file:
        data = pickle.load(pkl_file)
    return data
