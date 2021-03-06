class Board(object):
    def __init__(self):
        self.is_player_1s_turn = True
        self.player = 1
        self.current_board = self.initial_board()
        self.player_1_pit = 6
        self.player_2_pit = 13
        self.game_over = False
        self.winner = None
        self.is_printing = False
        self.is_debug_printing = False
        self.pairs = {0: 12, 1: 11, 2: 10,  3: 9,  4: 8,  5: 7,
                      7:  5, 8:  4, 9:  3, 10: 2, 11: 1, 12: 0}

    def __str__(self):
        return "Board object for game Mancala"

    @staticmethod
    def initial_board():
        # Returns a representation of the starting state of the game
        # The 14th index represents whose turn it is.
        #   4  4  4 | 4  4  4       12 11 10 | 9  8  7
        # 0                   0  13                   6 1st players home
        #   4  4  4 | 4  4  4       0  1  2  | 3  4  5
        return [4, 4, 4, 4, 4, 4, 0, 4, 4, 4, 4, 4, 4, 0, 1]

    def process_move(self, move):
        switch_player = True

        # Check that the chosen move is a legal move
        if self.is_printing:
            print("Processing move {} for player {}"
                  .format(move, self.player))
        if move not in self.get_legal_moves():
            # legal moves is the values of the moves not the indexes
            print("Not a valid move.")
            return

        # Get the marbles from the hole.
        marbles = self.current_board[move]
        self.current_board[move] = 0
        if self.is_debug_printing:
            print("Marbles in pit {} is {}".format(move, marbles))

        # Place the marbles around the board. Skipping opponent home
        pit_to_add = move
        if self.is_debug_printing:
            print("pit to add {}".format(pit_to_add))
        for _ in range(marbles):
            pit_to_add = self.get_pit_to_add(pit_to_add)
            if self.is_debug_printing:
                print("in for loop for placing marbles. Adding to {}"
                      .format(pit_to_add))
            self.current_board[pit_to_add] += 1  # add 1 marble to pit

        # Check if pit was empty, steal from opponent only on your side
        if self.current_board[pit_to_add] == 1 \
                and self.own_side_pit(pit_to_add):
            self.steal_marbles(pit_to_add)

        # if pit_to_add is own home then free turn, don't switch players
        if self.own_home(pit_to_add):
            switch_player = False

        # Check for the win conditions.
        if self.current_board[self.player_1_pit] > 24 or \
                self.current_board[self.player_2_pit] > 24 or \
                self.marbles_gone_on_one_side():
            self.clean_up_winning_marbles()
            self.game_over = True
            switch_player = False

        if switch_player:
            self.switch_player()

    @staticmethod
    def policy_for_legal_moves(legal_moves, policy):
        policy = [policy[index] for index in legal_moves]

        # Normalize the policy to solve known issue with numpy
        policy_sum = sum(policy)
        policy = [x / policy_sum for x in policy]

        return policy

    @staticmethod
    def policy_dict_for_legal_moves(legal_moves, policy):
        p_dict = dict(enumerate(policy))
        p_dict = {k: v for k, v in p_dict.items() if k in legal_moves}
        policy_sum = sum(p_dict.values())
        p_dict = {k: v / policy_sum for k, v in p_dict.items()}

        return p_dict

    def get_legal_moves(self):
        filtered = list(map(lambda x: x[0],
                            filter(lambda x: x[1] != 0,
                                   enumerate(self.current_board))))

        # Remove player homes from legal moves
        if self.player_1_pit in filtered:
            filtered.remove(self.player_1_pit)
        if self.player_2_pit in filtered:
            filtered.remove(self.player_2_pit)

        board_side = list(filter(lambda x: x < 6, filtered)) \
            if self.is_player_1s_turn \
            else list(filter(lambda x: 6 < x < 14, filtered))

        return board_side

    def switch_player(self):
        self.is_player_1s_turn = not self.is_player_1s_turn
        self.player = 1 if self.is_player_1s_turn else 2
        self.current_board[14] = self.player

    def get_whose_turn(self):
        return 1 if self.is_player_1s_turn else 2

    def get_pit_to_add(self, pit_to_increment):
        pit = (pit_to_increment + 1) % 14
        if self.is_debug_printing:
            print("Pit to increment is: {}".format(pit_to_increment))

        if self.enemy_home(pit):
            if self.is_debug_printing:
                print("\t\tPit is enemy home. Skip it")
            pit += 1
            pit = pit % 14

        if self.is_debug_printing:
            print("Previous pit is {}, new pit is {}"
                  .format(pit_to_increment, pit))

        return pit

    def enemy_home(self, pit_to_add):
        enemy_home = pit_to_add == self.player_2_pit \
            if self.is_player_1s_turn \
            else pit_to_add == self.player_1_pit
        return enemy_home

    def own_home(self, pit_to_add):
        own_home = pit_to_add == self.player_1_pit \
            if self.is_player_1s_turn \
            else pit_to_add == self.player_2_pit
        return own_home

    def is_tie(self):
        return self.current_board[6] == self.current_board[13]

    def get_winner(self):
        one = self.current_board[6]
        two = self.current_board[13]
        if self.is_printing:
            print("Player 1: {}, Player 2: {}".format(one, two))
        compare = (one > two) - (one < two)

        if self.is_printing:
            print("Winner is: {}".format(compare))
        return compare

    def get_winner_string(self):
        winner = self.get_winner()
        if winner == 0:
            to_return = "Tie!"
        else:
            to_return = "Player 1" if winner == 1 else "Player 2"
        return to_return

    def is_game_over(self):
        return self.game_over

    def marbles_gone_on_one_side(self):
        side1 = self.current_board[:6]
        if len(list(filter(lambda x: x == 0, side1))) == 6:
            return True

        side2 = self.current_board[7:13]
        if len(list(filter(lambda x: x == 0, side2))) == 6:
            return True

        return False

    def print_current_board(self):
        print("\n\nPlayer {}'s turn".format(self.current_board[14]))
        print("         12:{}  11:{}  10:{}  9:{}  8:{}  7:{}".format(
                                                self.current_board[12],
                                                self.current_board[11],
                                                self.current_board[10],
                                                self.current_board[9],
                                                self.current_board[8],
                                                self.current_board[7]))
        print("2P Home:{}                                1P Home:{}".
              format(self.current_board[13], self.current_board[6]))
        print("         0:{}   1:{}   2:{}   3:{}  4:{}  5:{}".format(
                                                self.current_board[0],
                                                self.current_board[1],
                                                self.current_board[2],
                                                self.current_board[3],
                                                self.current_board[4],
                                                self.current_board[5]))

    def board_key(self):
        return "0:{}   1:{}  2:{}  3:{}  4:{}  5:{}  6:{}  7:{}  " \
               "8:{}  9:{}  10:{}   11:{}   12:{}  13:{}".format(
                                                self.current_board[0],
                                                self.current_board[1],
                                                self.current_board[2],
                                                self.current_board[3],
                                                self.current_board[4],
                                                self.current_board[5],
                                                self.current_board[6],
                                                self.current_board[7],
                                                self.current_board[8],
                                                self.current_board[9],
                                                self.current_board[10],
                                                self.current_board[11],
                                                self.current_board[12],
                                                self.current_board[13])

    def current_board_str(self):
        return "Player {}'s turn" \
            "\n         12:{}  11:{}  10:{}  9:{}  8:{}  7:{}" \
            "\n2P Home:{}                                1P Home:{}" \
            "\n         0:{}   1:{}   2:{}   3:{}  4:{}  5:{}".format(
                                                self.current_board[14],
                                                self.current_board[12],
                                                self.current_board[11],
                                                self.current_board[10],
                                                self.current_board[9],
                                                self.current_board[8],
                                                self.current_board[7],
                                                self.current_board[13],
                                                self.current_board[6],
                                                self.current_board[0],
                                                self.current_board[1],
                                                self.current_board[2],
                                                self.current_board[3],
                                                self.current_board[4],
                                                self.current_board[5])

    def clean_up_winning_marbles(self):
        if self.is_debug_printing:
            print("Total before {}".format(self.current_board[6]))
        for x in range(6):
            if self.is_debug_printing:
                print("x: {}".format(x))
            to_add = self.current_board[x]
            self.current_board[x] = 0
            self.current_board[6] += to_add

        if self.is_debug_printing:
            print("Total after {}".format(self.current_board[6]))
            print("Total marbles for second player")
            print("Total before {}".format(self.current_board[13]))

        for x in range(7, 13):
            if self.is_debug_printing:
                print("x: {}".format(x))
            to_add = self.current_board[x]
            self.current_board[x] = 0
            self.current_board[13] += to_add
        if self.is_debug_printing:
            print("Total after {}".format(self.current_board[13]))

    def get_opposite_pit(self, pit):
        return self.pairs.get(pit)

    def own_side_pit(self, pit_to_add):
        own_pit = pit_to_add < 6 if self.is_player_1s_turn \
            else 6 < pit_to_add < 13
        return own_pit

    def steal_marbles(self, pit_to_add):
        # Check the opposing side pit when zero
        opponent_pit = self.get_opposite_pit(pit_to_add)
        opponent_amount = self.current_board[opponent_pit]
        if opponent_amount == 0:
            return

        amount_to_add = 1
        self.current_board[pit_to_add] = 0
        amount_to_add += self.current_board[opponent_pit]
        if self.is_printing:
            print("Pit was empty. Steal the opponent marbles")
            print("Stole {} marbles from your opponent!"
                  .format(self.current_board[opponent_pit]))
        self.current_board[opponent_pit] = 0

        # Add stolen marbles to current player's pit
        own_home = self.player_1_pit if self.is_player_1s_turn \
            else self.player_2_pit
        self.current_board[own_home] += amount_to_add
