# English alphabet used by both encryption techniques
alphabet = 'abcdefghijklmnopqrstuvwxyz'


# Rotate a substitution table to the right
# This function is useful for checking how the recovered key changes between blocks
def rotate_table(table, rotations):
    rotations = rotations % len(table)

    if rotations == 0:
        return table

    return table[-rotations:] + table[:-rotations]


# Reverse the Caesar shift for a block
# The shift comes from the next recovered plaintext letter
def decrypt_caesar_block(cipherblock, shift):
    plaintext = []

    for char in cipherblock:
        cipher_index = alphabet.index(char)
        plain_index = (cipher_index - shift) % 26
        plaintext.append(alphabet[plain_index])

    return ''.join(plaintext)
