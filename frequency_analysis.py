from cipher_utils import alphabet


# Read the letters from one block, either encrypted or recovered
# The recovered letters are still a guess because the key is unknown
def get_block_text(block, use_plaintext=False):
    if use_plaintext:
        block_text = block['plaintext']
    else:
        block_text = ''.join(block['letters'])

    return block_text


# Count single letters in the selected blocks
def letter_frequency(blocks, use_plaintext=False):
    counts = {}

    for char in alphabet:
        counts[char] = 0

    for block in blocks:
        block_text = get_block_text(block, use_plaintext)

        for char in block_text:
            if char in alphabet:
                counts[char] += 1

    return counts


# Count sequences of a given size in a string of letters
def count_in_text(text, size, counts):
    for position in range(len(text) - size + 1):
        sequence = text[position:position + size]

        if all(char in alphabet for char in sequence):
            if sequence not in counts:
                counts[sequence] = 0
            counts[sequence] += 1

    return counts


# Count digrams or trigrams in the selected blocks
# By default, sequences cannot cross from one cipher block to another
# Cross-block counting joins only blocks that were originally next to each other
def count_sequences(blocks, size, use_plaintext=False, cross_blocks=False):
    counts = {}

    if not cross_blocks:
        for block in blocks:
            block_text = get_block_text(block, use_plaintext)
            count_in_text(block_text, size, counts)

    else:
        current_text = ''
        previous_end = None

        for block in blocks:
            block_text = get_block_text(block, use_plaintext)

            if previous_end is not None and block['start'] != previous_end:
                count_in_text(current_text, size, counts)
                current_text = ''

            current_text += block_text
            previous_end = block['end']

        count_in_text(current_text, size, counts)

    return counts


# Count the frequency of every two-letter sequence
def digram_frequency(blocks, use_plaintext=False, cross_blocks=False):
    return count_sequences(blocks, 2, use_plaintext, cross_blocks)


# Count the frequency of every three-letter sequence
def trigram_frequency(blocks, use_plaintext=False, cross_blocks=False):
    return count_sequences(blocks, 3, use_plaintext, cross_blocks)


# Calculate the percentage represented by each letter or sequence
def frequency_percentages(counts):
    total = sum(counts.values())
    percentages = {}

    for sequence, count in counts.items():
        if total > 0:
            percentages[sequence] = round(count / total * 100, 2)
        else:
            percentages[sequence] = 0.0

    return percentages


# The index of coincidence measures how often two randomly chosen letters match
# English often has a higher value than randomly distributed A-Z letters
def index_of_coincidence(counts):
    total = sum(counts.values())

    if total < 2:
        return 0.0

    matches = 0

    for count in counts.values():
        matches += count * (count - 1)

    return matches / (total * (total - 1))


# Approximate standard English letter frequencies for the visual comparison
# https://cs.wellesley.edu/~fturbak/codman/letterfreq.html
english_letter_percentages = {
    'a': 8.17, 'b': 1.49, 'c': 2.78, 'd': 4.25, 'e': 12.70,
    'f': 2.23, 'g': 2.02, 'h': 6.09, 'i': 6.97, 'j': 0.15,
    'k': 0.77, 'l': 4.03, 'm': 2.41, 'n': 6.75, 'o': 7.51,
    'p': 1.93, 'q': 0.10, 'r': 5.99, 's': 6.33, 't': 9.06,
    'u': 2.76, 'v': 0.98, 'w': 2.36, 'x': 0.15, 'y': 1.97,
    'z': 0.07
}
