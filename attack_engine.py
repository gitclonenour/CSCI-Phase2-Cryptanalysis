import math
import random
import os

from cipher_utils import alphabet, decrypt_caesar_block
from frequency_analysis import letter_frequency


# read the ciphertext from a file
def read_ciphertext(file_path):
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        ciphertext = file.read()
    return ciphertext


# extract the English letters and their positions from the ciphertext
def extract_letters(ciphertext):
    letters = []
    positions = []

    english_letters = alphabet + alphabet.upper() # the alphabet list from cipher_utils.py

    for index, char in enumerate(ciphertext): # co through every single character in the ciphertext
        if char in english_letters: # ignore spaces punctuation and non-English letters
            letters.append(char.lower())
            positions.append(index)

    return letters, positions


# identify the Caesar and monoalphabetic blocks
def identify_blocks(letters):
    blocks = []
    current_position = 0 # Current position in the letters list
    block_number = 0 # Current block number
    mono_uses = 0 # Number of monoalphabetic blocks used

    while current_position < len(letters):
        if block_number % 2 == 0: # Even block number: Caesar cipher
            block_type = 'caesar'
            block_size = 6
            rotation = None
        else: # Odd block number: Monoalphabetic substitution
            block_type = 'mono'
            block_size = 8
            rotation = mono_uses // 3 # The table rotates after every 3 mono blocks
            mono_uses += 1

        # Extract the current block
        block_letters = letters[current_position:current_position + block_size]

        # Store the information for this block
        block = {
            'number': block_number,
            'type': block_type,
            'start': current_position,
            'end': current_position + len(block_letters),
            'letters': block_letters,
            'rotation': rotation,
            'plaintext': '',
            'lookahead': None,
            'shift': None
        }

        blocks.append(block)

        # Move to the next block
        current_position += len(block_letters)
        block_number += 1

    return blocks


# Restore the spaces and punctuation in the recovered plaintext
def reconstruct_text(ciphertext, plaintext_letters, positions):
    if len(plaintext_letters) != len(positions):
        raise ValueError('The number of recovered letters does not match the ciphertext.')

    reconstructed = list(ciphertext)

    for index, position in enumerate(positions):
        reconstructed[position] = plaintext_letters[index]

    return ''.join(reconstructed)


# Load general English text to learn which letter sequences are common
# This is NOT the original message
def read_english_reference():
    current_folder = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_folder, 'english_reference.txt')

    with open(file_path, 'r', encoding='utf-8') as file:
        reference_text = file.read()

    return reference_text


# Count English trigrams and four-letter sequences in the reference text
def build_english_model(reference_text):
    letters = []

    for char in reference_text.lower():
        if char in alphabet:
            letters.append(char)

    english_text = ''.join(letters)

    if len(english_text) < 500:
        raise ValueError('The English reference needs at least 500 letters.')

    model = {}

    for size in [3, 4]:
        counts = {}

        for position in range(len(english_text) - size + 1):
            sequence = english_text[position:position + size]
            counts[sequence] = counts.get(sequence, 0) + 1

        total = len(english_text) - size + 1
        scores = {}

        for sequence in counts:
            scores[sequence] = math.log10(counts[sequence] / total)

        model[size] = {
            'scores': scores,
            'missing_score': math.log10(0.01 / total)
        }

    return model


# Give a higher score to plaintext that looks more like English
# We use trigrams and four-letter sequences instead of assuming any secret key
def score_english(plaintext_letters, model):
    if not plaintext_letters:
        return 0.0

    final_score = 0.0
    total_weight = 0.0

    for size in [3, 4]:
        number_of_sequences = len(plaintext_letters) - size + 1

        if number_of_sequences <= 0:
            continue

        weight = 0.4 if size == 3 else 1.0
        scores = model[size]['scores']
        missing_score = model[size]['missing_score']
        current_score = 0.0

        for position in range(number_of_sequences):
            sequence = plaintext_letters[position:position + size]
            current_score += scores.get(sequence, missing_score)

        final_score += weight * (current_score / number_of_sequences)
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return final_score / total_weight


# Make an initial key guess using single-letter frequency analysis
# key_guess[cipher_index] tells us the GUESSED original plaintext letter index
def guess_initial_key(blocks):
    mono_blocks = []

    for block in blocks:
        if block['type'] == 'mono':
            mono_blocks.append(block)

    letter_counts = letter_frequency(mono_blocks)

    # Rank ciphertext letters from most common to least common
    ranked_cipher_letters = sorted(letter_counts, key=lambda char: letter_counts[char], reverse=True)
    common_english_letters = 'etaoinshrdlcumwfgypbvkjxqz'
    key_guess = [0] * 26

    for index in range(26):
        cipher_letter = ranked_cipher_letters[index]
        plain_letter = common_english_letters[index]
        key_guess[alphabet.index(cipher_letter)] = alphabet.index(plain_letter)

    return key_guess


# Decrypt the letters with a GUESSED substitution key
# First we recover mono blocks, then use those letters to recover Caesar shifts
def decrypt_with_guess(letters, blocks, key_guess):
    plaintext = [''] * len(letters)

    # Decrypt mono blocks first, using the public rotation rule
    for block in blocks:
        if block['type'] == 'mono':
            rotation = block['rotation']

            for position in range(block['start'], block['end']):
                cipher_index = alphabet.index(letters[position])
                plain_index = (key_guess[cipher_index] + rotation) % 26
                plaintext[position] = alphabet[plain_index]

    # The Caesar shift depends on the first plaintext letter of the next block
    for block in blocks:
        if block['type'] == 'caesar':
            end = block['end']

            if end < len(letters):
                lookahead = plaintext[end]
            else:
                lookahead = 'x' # No next letter: the algorithm assumes x

            shift = alphabet.index(lookahead)

            block_plaintext = decrypt_caesar_block(block['letters'], shift)

            for index, char in enumerate(block_plaintext):
                plaintext[block['start'] + index] = char

    return ''.join(plaintext)


# Convert our guessed mapping into a substitution table for display
# The output is the key we DISCOVERED, not a key that was supplied to us
def get_guessed_table(key_guess):
    table = [''] * 26

    for cipher_index in range(26):
        plain_index = key_guess[cipher_index]
        table[plain_index] = alphabet[cipher_index]

    return ''.join(table)


# Build the final results and explain the recovered steps for every block
def build_result(ciphertext, letters, positions, key_guess, score):
    blocks = identify_blocks(letters)
    recovered_letters = decrypt_with_guess(letters, blocks, key_guess)
    plaintext = reconstruct_text(ciphertext, recovered_letters, positions)

    for block in blocks:
        block['plaintext'] = recovered_letters[block['start']:block['end']]

        if block['type'] == 'caesar':
            if block['end'] < len(recovered_letters):
                lookahead = recovered_letters[block['end']]
            else:
                lookahead = 'x'

            block['lookahead'] = lookahead
            block['shift'] = alphabet.index(lookahead)

    result = {
        'ciphertext': ciphertext,
        'plaintext': plaintext,
        'blocks': blocks,
        'guessed_table': get_guessed_table(key_guess),
        'score': score
    }

    return result


# Test how well a key guess turns ciphertext into English
def check_guess(key_guess, letters, blocks, english_model):
    plaintext_letters = decrypt_with_guess(letters, blocks, key_guess)
    return score_english(plaintext_letters, english_model)


# Finding the substitution key (this is the most important part of our attack Prof. Kevser)!
def attack_ciphertext_only(ciphertext, restarts=12, steps=3000, seed=42):
    if restarts < 1 or steps < 1:
        raise ValueError('Restarts and steps must both be greater than zero.')

    letters, positions = extract_letters(ciphertext)
    blocks = identify_blocks(letters)

    mono_letters = 0
    for block in blocks:
        if block['type'] == 'mono':
            mono_letters += len(block['letters'])

    # I noticed that short messages might be only a caesar block, this solves it (no substitution key is needed)
    if mono_letters == 0:
        result = build_result(ciphertext, letters, positions, list(range(26)), 0.0)
        result['guessed_table'] = None # No substitution key is needed or recovered
        result['mono_letters'] = 0
        return [result]

    reference_text = read_english_reference()
    english_model = build_english_model(reference_text)
    random_generator = random.Random(seed) # Make testing reproducible

    # Analysis only uses the first 1200 letters to guess a substitution key for efficiency purposes, then applies that key to the entire ciphertext
    search_letters = letters[:1200]
    search_blocks = identify_blocks(search_letters)

    best_key = guess_initial_key(search_blocks)
    best_score = check_guess(best_key, search_letters, search_blocks, english_model)
    candidates = []

    for restart in range(restarts):
        current_key = best_key.copy() # Starting a new search with the best key we foudn so far
        # Every search is a 'restart' that starts with a different random key guess

        if restart > 0:
            # Start again with some shuffled letters to find another possible key
            for unused in range(random_generator.randint(4, 12)): # shuffle between 4 and 12 pairs of letters to get a new starting key
                first, second = random_generator.sample(range(26), 2)
                current_key[first], current_key[second] = current_key[second], current_key[first]

        # Check how well our guessed key turns the ciphertext into English
        current_score = check_guess(current_key, search_letters, search_blocks, english_model)
        restart_best_key = current_key.copy()
        restart_best_score = current_score

        for step in range(steps):
            # Randomly swap two letters in our guessed substitution key
            first, second = random_generator.sample(range(26), 2)
            current_key[first], current_key[second] = current_key[second], current_key[first]

            # Check if the new key produces plaintext that looks more like English
            new_score = check_guess(current_key, search_letters, search_blocks, english_model)

            if new_score > current_score:
                # Keep the new key if it gives us a better score
                current_score = new_score

                # Save the best key found during this restart
                if current_score > restart_best_score:
                    restart_best_score = current_score
                    restart_best_key = current_key.copy()

                # Save the best key found across all restarts
                if current_score > best_score:
                    best_score = current_score
                    best_key = current_key.copy()

            else:
                # If the new key is not better, undo the swap and try again
                current_key[first], current_key[second] = current_key[second], current_key[first]

        candidates.append((restart_best_score, restart_best_key))

    candidates.append((best_score, best_key))

    # Keep up to three different candidate keys, ranked by their English scores
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    unique_tables = []
    results = []

    for score, key_guess in candidates:
        table = get_guessed_table(key_guess)

        if table not in unique_tables:
            unique_tables.append(table)
            result = build_result(ciphertext, letters, positions, key_guess, score)
            result['mono_letters'] = mono_letters
            results.append(result)

        if len(results) == 3:
            break

    return results
