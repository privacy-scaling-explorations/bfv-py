from bfv.fft import recursive_fft, recursive_ifft
import random
import copy

class PolynomialRing:
    def __init__(self, n: int, modulus: int) -> None:
        """
        Initialize a polynomial ring R_modulus = Z_modulus[x]/f(x) where f(x)=x^n+1.
        - modulus is a prime number.
        - n is a power of 2.
        """

        assert n > 0 and (n & (n - 1)) == 0, "n must be a power of 2"

        fx = [1] + [0] * (n - 1) + [1]

        self.denominator = fx
        self.modulus = modulus
        self.n = n

    def sample_polynomial(self) -> "Polynomial":
        """
        Sample polynomial from the ring
        """

        # range for random.randint
        lower_bound = - (self.modulus - 1) / 2 # inclusive
        upper_bound = (self.modulus - 1) / 2 # inclusive

        # assert that the bounds float are integers namely the decimal part is 0
        assert lower_bound % 1 == 0 and upper_bound % 1 == 0
    
        # generate n random coefficients in the range [lower_bound, upper_bound]
        coeffs = [random.randint(int(lower_bound), int(upper_bound)) for _ in range(self.n)]

        return Polynomial(coeffs)

    def __eq__(self, other) -> bool:
        if isinstance(other, PolynomialRing):
            return (
                self.denominator == other.denominator and self.modulus == other.modulus
            )
        return False


class Polynomial:
    def __init__(self, coefficients: list[int]):
        """
        Initialize a polynomial with the given coefficients starting from the highest degree coefficient.
        """
        self.coefficients = coefficients

    def reduce_coefficients_by_modulus(self, modulus: int) -> None:
        """
        Reduce the coefficients of the polynomial by the modulus of the polynomial ring.
        """
        for i in range(len(self.coefficients)):
            self.coefficients[i] = get_centered_remainder(self.coefficients[i], modulus)

    def reduce_coefficients_by_cyclo(self, cyclo: list[int]) -> None:
        """
        Reduce the coefficients by dividing it by the cyclotomic polynomial and returning the remainder.
        The cyclotomic polynomial is x^n+1.
        """
        _, remainder = poly_div(self.coefficients, cyclo)

        n = len(cyclo) - 1

        # pad the remainder with zeroes to make it len=n
        remainder = [0] * (n - len(remainder)) + remainder

        assert len(remainder) == n

        self.coefficients = remainder

    def reduce_in_ring(self, ring: PolynomialRing) -> None:
        """
        Reduce the coefficients of the polynomial by the modulus of the polynomial ring and by the denominator of the polynomial ring.
        """
        self.reduce_coefficients_by_cyclo(ring.denominator)
        self.reduce_coefficients_by_modulus(ring.modulus)

    def __add__(self, other) -> "Polynomial":
        return Polynomial(poly_add(self.coefficients, other.coefficients))

    def __mul__(self, other) -> "Polynomial":
        return Polynomial(poly_mul(self.coefficients, other.coefficients))
    
    def evaluate(self, x: int) -> int:
        """
        Evaluate the polynomial at x.
        """
        result = 0
        for coeff in self.coefficients:
            result = result * x + coeff
        return result
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Polynomial):
            return self.coefficients == other.coefficients
        return False


def poly_div(dividend: list[int], divisor: list[int]) -> tuple[list[int], list[int]]:
    # Initialize quotient and remainder
    quotient = [0] * (len(dividend) - len(divisor) + 1)
    remainder = list(dividend)

    # Main division loop
    for i in range(len(quotient)):
        coeff = (
            remainder[i] // divisor[0]
        )  # Calculate the leading coefficient of quotient
        # turn coeff into an integer
        coeff = coeff
        quotient[i] = coeff

        # Subtract the current divisor*coeff from the remainder
        for j in range(len(divisor)):
            rem = remainder[i + j]
            rem -= divisor[j] * coeff
            remainder[i + j] = rem

    # Remove leading zeroes in remainder, if any
    while remainder and remainder[0] == 0:
        remainder.pop(0)

    return quotient, remainder


def poly_mul(poly1: list[int], poly2: list[int]) -> list[int]:

    product_len = len(poly1) + len(poly2) - 1

    # pad the coefficients with zeroes at the beginning to make them the same length of product_len (https://math.stackexchange.com/questions/764727/concrete-fft-polynomial-multiplication-example/764870#764870)
    # that's because we need to be able to compute #product_len points during convolution
    poly1_padded = [0] * (product_len - len(poly1)) + poly1
    poly2_padded = [0] * (product_len - len(poly2)) + poly2

    # fft works when the length of the coefficients is a power of 2
    n = 1
    while n < product_len:
        n *= 2
    
    # further pad the coefficients with zeroes at the beginning to make them of length n (power of two)
    poly1_padded = [0] * (n - product_len) + poly1_padded
    poly2_padded = [0] * (n - product_len) + poly2_padded

    poly1_reversed = copy.deepcopy(poly1_padded)
    poly2_reversed = copy.deepcopy(poly2_padded)

    poly1_reversed.reverse()
    poly2_reversed.reverse()

    # turn the polynomials into their point form using FFT O(n log n)
    fft_evals1 = recursive_fft(poly1_reversed)
    fft_evals2 = recursive_fft(poly2_reversed)

    # multiply the polynomials in point form to get the product in point form O(n)
    fft_product_evals = [fft_evals1[i] * fft_evals2[i] for i in range(n)]

    # turn the product back into its coefficient form using IFFT O(n log n)
    product_coeffs = recursive_ifft(fft_product_evals)

    # calculate the padding for product_coeffs
    product_padding = len(product_coeffs) - product_len

    product_coeffs_no_pad = product_coeffs[:-product_padding] if product_padding else product_coeffs[:]

    # reverse the product_coeffs_no_pad list to obtain an array in which the first element is the highest degree coefficient
    product_coeffs_no_pad.reverse()

    product_coeffs = [int(coeff.real) for coeff in product_coeffs_no_pad]

    return product_coeffs


def poly_add(poly1: list[int], poly2: list[int]) -> list[int]:
    # Find the length of the longer polynomial
    max_length = max(len(poly1), len(poly2))
    
    # Pad the shorter polynomial with zeros at the beginning
    poly1 = [0] * (max_length - len(poly1)) + poly1
    poly2 = [0] * (max_length - len(poly2)) + poly2

    # Add corresponding coefficients
    result = [poly1[i] + poly2[i] for i in range(max_length)]
    
    return result


def get_centered_remainder(x, modulus) -> int:
    """
    Returns the centered remainder of x with respect to modulus.
    """
    r = x % modulus
    return r if r <= modulus / 2 else r - modulus

def get_standard_form(x, modulus) -> int:
    """
    Returns the standard form of x with respect to modulus.
    """
    r = x % modulus
    return r if r >= 0 else r + modulus

def poly_mul_naive(poly1: list[int], poly2: list[int]) -> list[int]:
    """
    Naive polynomial multiplication
    """
    product_len = len(poly1) + len(poly2) - 1
    product = [0] * product_len

    # Multiply each term of the first polynomial by each term of the second polynomial
    for i in range(len(poly1)):
        for j in range(len(poly2)):
            product[i + j] += poly1[i] * poly2[j]

    return product