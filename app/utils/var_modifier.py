import random
import jellyfish
from typing import List, Dict, Tuple
import re
import Levenshtein
from app.utils.rule_evaluator import evaluate_rule_compliance

def modify_variations_to_match_config(
    original_name: str, 
    existing_variations: List[str], 
    config: Dict
) -> List[str]:
    """
    Modify existing variations to match the configuration requirements.
    Intelligently analyzes existing variations and makes targeted modifications.
    
    Args:
        original_name: The original seed name
        existing_variations: List of existing variations to modify
        config: Configuration dictionary with similarity distributions and rules
        
    Returns:
        Modified list of variations that match the config requirements
    """
    
    # Extract configuration parameters
    variation_count = config.get('variation_per_seed_name', 8)
    phonetic_dist = config.get('phonetic_similarity_distribution', {})
    orthographic_dist = config.get('orthographic_similarity_distribution', {})
    rule_transformation_dist = config.get('rule_transformation', {})

    # Calculate target counts for each similarity level
    phonetic_targets = {
        'light': phonetic_dist.get('light', {}).get('number', 0),
        'medium': phonetic_dist.get('medium', {}).get('number', 0),
        'far': phonetic_dist.get('far', {}).get('number', 0)
    }
    
    orthographic_targets = {
        'light': orthographic_dist.get('light', {}).get('number', 0),
        'medium': orthographic_dist.get('medium', {}).get('number', 0),
        'far': orthographic_dist.get('far', {}).get('number', 0)
    }
    
    print(f"\nAnalyzing variations for: {original_name}")
    print(f"Target counts - Phonetic: {phonetic_targets}, Orthographic: {orthographic_targets}")
    
    # Step 1: Analyze existing variations
    variation_analysis = analyze_existing_variations(original_name, existing_variations)
    
    # Step 2: Adjust variations to match phonetic distribution
    phonetic_adjusted = adjust_phonetic_distribution_smart(
        original_name, existing_variations, phonetic_targets, variation_analysis
    )

    # Step 3: Adjust variations to match orthographic distribution
    final_variations = adjust_orthographic_distribution_smart(
        original_name, phonetic_adjusted, orthographic_targets, variation_count
    )
    
    # Step 4: Print final analysis in the same format
    print(f"\nModified variations for: {original_name}")
    print_analysis_in_format(original_name, final_variations, phonetic_targets, orthographic_targets)
    
    return final_variations[:variation_count]



def analyze_existing_variations(original_name: str, variations: List[str]) -> Dict:
    """
    Analyze existing variations and categorize them by similarity levels.
    """
    analysis = {
        'phonetic': {'light': [], 'medium': [], 'far': []},
        'orthographic': {'light': [], 'medium': [], 'far': []},
        'variations_with_scores': []
    }
    
    for variation in variations:
        phonetic_score = calculate_phonetic_similarity(original_name, variation)
        orthographic_score = calculate_orthographic_similarity(original_name, variation)
        
        # Categorize by phonetic similarity
        if 0.80 <= phonetic_score <= 1.00:
            analysis['phonetic']['light'].append((variation, phonetic_score))
        elif 0.60 <= phonetic_score < 0.80:
            analysis['phonetic']['medium'].append((variation, phonetic_score))
        else:
            analysis['phonetic']['far'].append((variation, phonetic_score))
        
        # Categorize by orthographic similarity
        if 0.70 <= orthographic_score <= 1.00:
            analysis['orthographic']['light'].append((variation, orthographic_score))
        elif 0.50 <= orthographic_score < 0.70:
            analysis['orthographic']['medium'].append((variation, orthographic_score))
        else:
            analysis['orthographic']['far'].append((variation, orthographic_score))
        
        analysis['variations_with_scores'].append({
            'variation': variation,
            'phonetic_score': phonetic_score,
            'orthographic_score': orthographic_score
        })
    
    # Sort by scores within each category
    for category in ['light', 'medium', 'far']:
        analysis['phonetic'][category].sort(key=lambda x: x[1], reverse=True)
        analysis['orthographic'][category].sort(key=lambda x: x[1], reverse=True)
    
    return analysis

def adjust_phonetic_distribution_smart(
    original_name: str, 
    variations: List[str], 
    targets: Dict[str, int],
    analysis: Dict
) -> List[str]:
    """
    Intelligently adjust variations to match phonetic distribution targets.
    """
    result_variations = []
    used_variations = set()
    
    # First, use existing variations that already meet the targets
    for level in ['light', 'medium', 'far']:
        target_count = targets[level]
        existing_variations = analysis['phonetic'][level]
        
        # Use existing variations up to the target count
        for i in range(min(target_count, len(existing_variations))):
            variation = existing_variations[i][0]
            if variation not in used_variations:
                result_variations.append(variation)
                used_variations.add(variation)
                print(f"  Used existing {level} phonetic variation: '{variation}'")
    
    # Generate additional variations for missing targets
    for level in ['light', 'medium', 'far']:
        target_count = targets[level]
        current_count = len([v for v in result_variations if v in [var[0] for var in analysis['phonetic'][level]]])
        
        while current_count < target_count:
            new_variation = generate_phonetic_variation(original_name, level)
            if new_variation not in used_variations:
                result_variations.append(new_variation)
                used_variations.add(new_variation)
                current_count += 1
                print(f"  Generated new {level} phonetic variation: '{new_variation}'")
    
    # Add remaining unused variations to fill the count
    for variation in variations:
        if len(result_variations) < sum(targets.values()) and variation not in used_variations:
            result_variations.append(variation)
            used_variations.add(variation)
            print(f"  Added remaining variation: '{variation}'")
    
    return result_variations

def adjust_orthographic_distribution_smart(
    original_name: str, 
    variations: List[str], 
    targets: Dict[str, int],
    total_count: int
) -> List[str]:
    """
    Intelligently adjust variations to match orthographic distribution targets.
    """
    # Re-analyze current variations
    current_analysis = analyze_existing_variations(original_name, variations)
    
    result_variations = []
    used_variations = set()
    
    print(f"  Orthographic targets: {targets}")
    print(f"  Current orthographic distribution: {len(current_analysis['orthographic']['light'])} light, {len(current_analysis['orthographic']['medium'])} medium, {len(current_analysis['orthographic']['far'])} far")
    
    # Calculate how many we need for each level
    needed = {}
    for level in ['light', 'medium', 'far']:
        target_count = targets[level]
        existing_count = len(current_analysis['orthographic'][level])
        needed[level] = max(0, target_count - existing_count)
        print(f"  Need {needed[level]} more {level} orthographic variations")
    
    # First, use existing variations that already meet the targets
    for level in ['light', 'medium', 'far']:
        target_count = targets[level]
        existing_variations = current_analysis['orthographic'][level]
        
        # Use existing variations up to the target count
        for i in range(min(target_count, len(existing_variations))):
            variation = existing_variations[i][0]
            if variation not in used_variations:
                result_variations.append(variation)
                used_variations.add(variation)
                print(f"  Used existing {level} orthographic variation: '{variation}'")
    
    # Generate additional variations for missing targets with loop protection
    for level in ['light', 'medium', 'far']:
        target_count = targets[level]
        current_count = len([v for v in result_variations if v in [var[0] for var in current_analysis['orthographic'][level]]])
        
        attempts = 0
        max_attempts = 50  # Prevent infinite loops
        
        while current_count < target_count and attempts < max_attempts:
            new_variation = generate_orthographic_variation(original_name, level)
            if new_variation and new_variation not in used_variations:
                # Verify the variation actually falls in the target range
                orthographic_score = calculate_orthographic_similarity(original_name, new_variation)
                is_correct_level = False
                
                if level == 'light' and 0.70 <= orthographic_score <= 1.00:
                    is_correct_level = True
                elif level == 'medium' and 0.50 <= orthographic_score < 0.70:
                    is_correct_level = True
                elif level == 'far' and 0.20 <= orthographic_score < 0.50:
                    is_correct_level = True
                
                if is_correct_level:
                    result_variations.append(new_variation)
                    used_variations.add(new_variation)
                    current_count += 1
                    print(f"  Generated new {level} orthographic variation: '{new_variation}' (score: {orthographic_score:.3f})")
                else:
                    print(f"  Generated variation '{new_variation}' has score {orthographic_score:.3f}, not in {level} range")
            
            attempts += 1
        
        if attempts >= max_attempts:
            print(f"  Warning: Could not generate enough {level} variations after {max_attempts} attempts")
    
    # Add remaining unused variations to fill the count
    for variation in variations:
        if len(result_variations) < total_count and variation not in used_variations:
            result_variations.append(variation)
            used_variations.add(variation)
            print(f"  Added remaining variation: '{variation}'")
    
    return result_variations[:total_count]
def adjust_rule_transformation_distribution_smart(original_name: str, variations: List[str], targets: Dict[str, int]):
    """
    Intelligently adjust variations to match rule transformation distribution targets.
    """
    # Re-analyze current variations
    compliance_results, compliance_ratio = evaluate_rule_compliance(original_name, variations, list(targets.keys()))
    print(f"  Rule transformation distribution: {compliance_results}")
    print(f"  Compliance ratio: {compliance_ratio}")
    return 
    
def print_analysis_in_format(
    original_name: str, 
    variations: List[str], 
    phonetic_targets: Dict[str, int], 
    orthographic_targets: Dict[str, int]
):
    """
    Print analysis in the same format as the original analyze_variation_distribution function.
    """
    # Calculate current distributions
    phonetic_counts = {'light': 0, 'medium': 0, 'far': 0}
    orthographic_counts = {'light': 0, 'medium': 0, 'far': 0}
    
    print(f"  Phonetic distribution:")
    for variation in variations:
        # Calculate phonetic similarity
        phonetic_score = calculate_phonetic_similarity(original_name, variation)
        if 0.80 <= phonetic_score <= 1.00:
            phonetic_counts['light'] += 1
        elif 0.60 <= phonetic_score < 0.80:
            phonetic_counts['medium'] += 1
        else:
            phonetic_counts['far'] += 1
        
        # Calculate orthographic similarity
        orthographic_score = calculate_orthographic_similarity(original_name, variation)
        if 0.70 <= orthographic_score <= 1.00:
            orthographic_counts['light'] += 1
        elif 0.50 <= orthographic_score < 0.70:
            orthographic_counts['medium'] += 1
        else:
            orthographic_counts['far'] += 1
    
    print(f"    Light: {phonetic_counts['light']}/{phonetic_targets['light']}")
    print(f"    Medium: {phonetic_counts['medium']}/{phonetic_targets['medium']}")
    print(f"    Far: {phonetic_counts['far']}/{phonetic_targets['far']}")
    
    print(f"  Orthographic distribution:")
    print(f"    Light: {orthographic_counts['light']}/{orthographic_targets['light']}")
    print(f"    Medium: {orthographic_counts['medium']}/{orthographic_targets['medium']}")
    print(f"    Far: {orthographic_counts['far']}/{orthographic_targets['far']}")
    
    # Show individual variation scores
    print(f"  Individual variations:")
    for variation in variations:
        p_score = calculate_phonetic_similarity(original_name, variation)
        o_score = calculate_orthographic_similarity(original_name, variation)
        print(f"    {variation}: p={p_score:.3f}, o={o_score:.3f}")

def generate_phonetic_variation(original_name: str, similarity_level: str) -> str:
    """
    Generate a variation with specific phonetic similarity level.
    """
    if similarity_level == 'light':
        return generate_light_phonetic_variation(original_name)
    elif similarity_level == 'medium':
        return generate_medium_phonetic_variation(original_name)
    else:  # far
        return generate_far_phonetic_variation(original_name)

def generate_orthographic_variation(original_name: str, similarity_level: str) -> str:
    """
    Generate a variation with specific orthographic similarity level.
    """
    if similarity_level == 'light':
        return generate_light_orthographic_variation(original_name)
    elif similarity_level == 'medium':
        return generate_medium_orthographic_variation(original_name)
    else:  # far
        return generate_far_orthographic_variation(original_name)

def generate_light_phonetic_variation(name: str) -> str:
    """Generate light phonetic variation (0.80-1.00 similarity)."""
    name_lower = name.lower()
    
    # Light transformations
    transformations = [
        lambda x: x + 'e' if not x.endswith('e') else x + 'h',
        lambda x: x + 'h' if not x.endswith('h') else x + 'e',
        lambda x: x.replace('c', 'k') if 'c' in x else x + 'e',
        lambda x: x.replace('k', 'c') if 'k' in x else x + 'e',
        lambda x: x.replace('s', 'c') if 's' in x else x + 'e',
        lambda x: x.replace('z', 's') if 'z' in x else x + 'e',
        lambda x: x.replace('f', 'ph') if 'f' in x else x + 'e',
        lambda x: x.replace('ph', 'f') if 'ph' in x else x + 'e',
        lambda x: x + 'e',
        lambda x: x + 'h',
        lambda x: x + 'y',
    ]
    
    transform = random.choice(transformations)
    variation = transform(name_lower)
    
    # Ensure we always get a different variation
    if variation == name_lower:
        variation = name_lower + random.choice(['e', 'h', 'y'])
    
    return variation.capitalize()

def generate_medium_phonetic_variation(name: str) -> str:
    """Generate medium phonetic variation (0.60-0.79 similarity)."""
    name_lower = name.lower()
    
    # Medium transformations
    transformations = [
        lambda x: x.replace('a', 'e') if 'a' in x else x + 'ie',
        lambda x: x.replace('e', 'a') if 'e' in x else x + 'ie',
        lambda x: x.replace('i', 'y') if 'i' in x else x + 'ie',
        lambda x: x.replace('o', 'u') if 'o' in x else x + 'ie',
        lambda x: x.replace('u', 'o') if 'u' in x else x + 'ie',
        lambda x: x.replace('t', 'tt') if 't' in x else x + 'ie',
        lambda x: x.replace('d', 'dd') if 'd' in x else x + 'ie',
        lambda x: x.replace('l', 'll') if 'l' in x else x + 'ie',
        lambda x: x + 'ie',
        lambda x: x + 'ey',
        lambda x: x + 'ay',
    ]
    
    transform = random.choice(transformations)
    variation = transform(name_lower)
    
    # Ensure we always get a different variation
    if variation == name_lower:
        variation = name_lower + random.choice(['ie', 'ey', 'ay'])
    
    return variation.capitalize()

def generate_far_phonetic_variation(name: str) -> str:
    """Generate far phonetic variation (0.30-0.59 similarity)."""
    name_lower = name.lower()
    
    # Far transformations
    transformations = [
        lambda x: x.replace('a', 'o') if 'a' in x else x + 'x',
        lambda x: x.replace('e', 'u') if 'e' in x else x + 'x',
        lambda x: x.replace('i', 'a') if 'i' in x else x + 'x',
        lambda x: x.replace('o', 'a') if 'o' in x else x + 'x',
        lambda x: x.replace('u', 'e') if 'u' in x else x + 'x',
        lambda x: x.replace('c', 'x') if 'c' in x else x + 'x',
        lambda x: x.replace('k', 'q') if 'k' in x else x + 'x',
        lambda x: x.replace('s', 'z') if 's' in x else x + 'x',
        lambda x: x + 'x',
        lambda x: x + 'q',
        lambda x: x + 'z',
    ]
    
    transform = random.choice(transformations)
    variation = transform(name_lower)
    
    # Ensure we always get a different variation
    if variation == name_lower:
        variation = name_lower + random.choice(['x', 'q', 'z'])
    
    return variation.capitalize()

def generate_light_orthographic_variation(name: str) -> str:
    """Generate light orthographic variation (0.70-1.00 similarity)."""
    name_lower = name.lower()
    
    # Light orthographic changes - very subtle changes to maintain high similarity
    transformations = [
        lambda x: x + 'e' if not x.endswith('e') else x + 'h',
        lambda x: x + 'h' if not x.endswith('h') else x + 'e',
        lambda x: x.replace('c', 'k') if 'c' in x else x + 'e',
        lambda x: x.replace('k', 'c') if 'k' in x else x + 'e',
        lambda x: x.replace('s', 'c') if 's' in x else x + 'e',
        lambda x: x.replace('z', 's') if 'z' in x else x + 'e',
        lambda x: x.replace('f', 'ph') if 'f' in x else x + 'e',
        lambda x: x.replace('ph', 'f') if 'ph' in x else x + 'e',
        lambda x: x + 'e',
        lambda x: x + 'h',
        lambda x: x + 'y',
        lambda x: x + 'a',
        lambda x: x[:-1] + 'e' if len(x) > 1 and x[-1] != 'e' else x + 'e',
        lambda x: x[:-1] + 'h' if len(x) > 1 and x[-1] != 'h' else x + 'h',
    ]
    
    # Try multiple transformations to ensure we get a good variation
    for _ in range(10):
        transform = random.choice(transformations)
        variation = transform(name_lower)
        
        # Ensure we always get a different variation
        if variation == name_lower:
            variation = name_lower + random.choice(['e', 'h', 'y', 'a'])
        
        # Check if this variation would be in the light range
        orthographic_score = calculate_orthographic_similarity(name, variation.capitalize())
        if 0.70 <= orthographic_score <= 1.00:
            return variation.capitalize()
    
    # Fallback: just add a suffix
    return (name_lower + random.choice(['e', 'h', 'y'])).capitalize()

def generate_medium_orthographic_variation(name: str) -> str:
    """Generate medium orthographic variation (0.50-0.69 similarity)."""
    name_lower = name.lower()
    
    # Medium orthographic changes - more aggressive to ensure medium similarity
    transformations = [
        lambda x: x.replace('a', 'e') if 'a' in x else x + 'ie',
        lambda x: x.replace('e', 'a') if 'e' in x else x + 'ie',
        lambda x: x.replace('i', 'y') if 'i' in x else x + 'ie',
        lambda x: x.replace('o', 'u') if 'o' in x else x + 'ie',
        lambda x: x.replace('u', 'o') if 'u' in x else x + 'ie',
        lambda x: x.replace('t', 'tt') if 't' in x else x + 'ie',
        lambda x: x.replace('d', 'dd') if 'd' in x else x + 'ie',
        lambda x: x.replace('l', 'll') if 'l' in x else x + 'ie',
        lambda x: x.replace('n', 'nn') if 'n' in x else x + 'ie',
        lambda x: x.replace('r', 'rr') if 'r' in x else x + 'ie',
        lambda x: x.replace('s', 'ss') if 's' in x else x + 'ie',
        lambda x: x + 'ie',
        lambda x: x + 'ey',
        lambda x: x + 'ay',
        lambda x: x + 'e' + 'y',
        lambda x: x + 'i' + 'e',
        lambda x: x[:-1] + 'ie' if len(x) > 1 else x + 'ie',
        lambda x: x[:-1] + 'ey' if len(x) > 1 else x + 'ey',
    ]
    
    # Try multiple transformations to ensure we get a good variation
    for _ in range(10):
        transform = random.choice(transformations)
        variation = transform(name_lower)
        
        # Ensure we always get a different variation
        if variation == name_lower:
            variation = name_lower + random.choice(['ie', 'ey', 'ay', 'e'])
        
        # Check if this variation would be in the medium range
        orthographic_score = calculate_orthographic_similarity(name, variation.capitalize())
        if 0.50 <= orthographic_score < 0.70:
            return variation.capitalize()
    
    # Fallback: just add a suffix
    return (name_lower + random.choice(['ie', 'ey', 'ay'])).capitalize()

def generate_far_orthographic_variation(name: str) -> str:
    """Generate far orthographic variation (0.20-0.49 similarity)."""
    name_lower = name.lower()
    
    # Far orthographic changes - more aggressive changes
    transformations = [
        lambda x: x.replace('a', 'o') if 'a' in x else x + 'x',
        lambda x: x.replace('e', 'u') if 'e' in x else x + 'x',
        lambda x: x.replace('i', 'a') if 'i' in x else x + 'x',
        lambda x: x.replace('o', 'a') if 'o' in x else x + 'x',
        lambda x: x.replace('u', 'e') if 'u' in x else x + 'x',
        lambda x: x.replace('c', 'x') if 'c' in x else x + 'x',
        lambda x: x.replace('k', 'q') if 'k' in x else x + 'x',
        lambda x: x.replace('s', 'z') if 's' in x else x + 'x',
        lambda x: x + 'x',
        lambda x: x + 'q',
        lambda x: x + 'z',
        lambda x: x.replace('a', 'o').replace('e', 'u') if 'a' in x or 'e' in x else x + 'x',
        lambda x: x.replace('i', 'a').replace('o', 'u') if 'i' in x or 'o' in x else x + 'x',
        lambda x: x[:-1] + 'x' if len(x) > 1 else x + 'x',
        lambda x: x[:-1] + 'q' if len(x) > 1 else x + 'q',
    ]
    
    # Try multiple transformations to ensure we get a good variation
    for _ in range(10):
        transform = random.choice(transformations)
        variation = transform(name_lower)
        
        # Ensure we always get a different variation
        if variation == name_lower:
            variation = name_lower + random.choice(['x', 'q', 'z'])
        
        # Check if this variation would be in the far range
        orthographic_score = calculate_orthographic_similarity(name, variation.capitalize())
        if 0.20 <= orthographic_score < 0.50:
            return variation.capitalize()
    
    # Fallback: just add a suffix
    return (name_lower + random.choice(['x', 'q', 'z'])).capitalize()

def generate_additional_variation(original_name: str, existing_variations: List[str]) -> str:
    """Generate an additional variation if needed."""
    name_lower = original_name.lower()
    
    # Simple transformations
    transformations = [
        lambda x: x + 'e',
        lambda x: x + 'h',
        lambda x: x + 'y',
        lambda x: x.replace('c', 'k'),
        lambda x: x.replace('k', 'c'),
        lambda x: x.replace('s', 'c'),
        lambda x: x.replace('z', 's'),
    ]
    
    for _ in range(10):  # Try up to 10 times
        transform = random.choice(transformations)
        variation = transform(name_lower)
        
        if variation not in [v.lower() for v in existing_variations]:
            return variation.capitalize()
    
    return None

def calculate_phonetic_similarity(original_name: str, variation: str) -> float:
    """
    Calculate phonetic similarity between two strings using a randomized subset of phonetic algorithms.
    This makes it harder for miners to game the system by not knowing which algorithms will be used.
    The selection and weighting are deterministic for each original_name.
    """
    # Define available phonetic algorithms
    algorithms = {
        "soundex": lambda x, y: jellyfish.soundex(x) == jellyfish.soundex(y),
        "metaphone": lambda x, y: jellyfish.metaphone(x) == jellyfish.metaphone(y),
        "nysiis": lambda x, y: jellyfish.nysiis(x) == jellyfish.nysiis(y),
        # Add more algorithms if needed
    }

    # Deterministically seed the random selection based on the original name
    random.seed(hash(original_name) % 10000)
    selected_algorithms = random.sample(list(algorithms.keys()), k=min(3, len(algorithms)))

    # Generate random weights that sum to 1.0
    weights = [random.random() for _ in selected_algorithms]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Calculate the weighted phonetic score
    phonetic_score = sum(
        algorithms[algo](original_name, variation) * weight
        for algo, weight in zip(selected_algorithms, normalized_weights)
    )

    return float(phonetic_score)

def calculate_orthographic_similarity(original_name: str, variation: str) -> float:
    """
    Calculate orthographic similarity between two strings using Levenshtein distance.
    
    Args:
        original_name: The original name
        variation: The variation to compare against
        
    Returns:
        Orthographic similarity score between 0 and 1
    """
    try:
        # Use Levenshtein distance to compare
        distance = Levenshtein.distance(original_name, variation)
        max_len = max(len(original_name), len(variation))
        
        # Calculate orthographic similarity score (0-1)
        return 1.0 - (distance / max_len)
    except Exception as e:
        print(f"Error calculating orthographic score: {str(e)}")
        return 0.0

def modify_variation_result_to_match_config(
    variation_result: Dict[str, List[str]], 
    config: Dict
) -> Dict[str, List[str]]:
    """
    Modify the entire variation_result dictionary to match configuration requirements.
    
    Args:
        variation_result: Dictionary with seed names as keys and lists of variations as values
        config: Configuration dictionary with similarity distributions and rules
        
    Returns:
        Modified variation_result dictionary that matches config requirements
    """
    modified_result = {}
    
    for seed_name, variations in variation_result.items():
        print(f"Processing seed name: {seed_name}")
        print(f"Original variations: {variations}")
        
        # Modify variations for this seed name
        modified_variations = modify_variations_to_match_config(
            seed_name, variations, config
        )
        
        modified_result[seed_name] = modified_variations
        
        print(f"Modified variations: {modified_variations}")
        print("-" * 40)
    
    return modified_result

def analyze_variation_distribution(
    variation_result: Dict[str, List[str]], 
    config: Dict
) -> Dict[str, Dict]:
    """
    Analyze the current distribution of variations against the target config.
    
    Args:
        variation_result: Dictionary with seed names as keys and lists of variations as values
        config: Configuration dictionary with similarity distributions and rules
        
    Returns:
        Analysis dictionary showing current vs target distributions
    """
    analysis = {}
    
    phonetic_dist = config.get('phonetic_similarity_distribution', {})
    orthographic_dist = config.get('orthographic_similarity_distribution', {})
    
    phonetic_targets = {
        'light': phonetic_dist.get('light', {}).get('number', 0),
        'medium': phonetic_dist.get('medium', {}).get('number', 0),
        'far': phonetic_dist.get('far', {}).get('number', 0)
    }
    
    orthographic_targets = {
        'light': orthographic_dist.get('light', {}).get('number', 0),
        'medium': orthographic_dist.get('medium', {}).get('number', 0),
        'far': orthographic_dist.get('far', {}).get('number', 0)
    }
    
    for seed_name, variations in variation_result.items():
        print(f"\nAnalyzing: {seed_name}")
        
        # Calculate current distributions
        phonetic_counts = {'light': 0, 'medium': 0, 'far': 0}
        orthographic_counts = {'light': 0, 'medium': 0, 'far': 0}
        
        for variation in variations:
            # Calculate phonetic similarity
            phonetic_score = calculate_phonetic_similarity(seed_name, variation)
            if 0.80 <= phonetic_score <= 1.00:
                phonetic_counts['light'] += 1
            elif 0.60 <= phonetic_score < 0.80:
                phonetic_counts['medium'] += 1
            else:
                phonetic_counts['far'] += 1
            
            # Calculate orthographic similarity
            orthographic_score = calculate_orthographic_similarity(seed_name, variation)
            if 0.70 <= orthographic_score <= 1.00:
                orthographic_counts['light'] += 1
            elif 0.50 <= orthographic_score < 0.70:
                orthographic_counts['medium'] += 1
            else:
                orthographic_counts['far'] += 1
        
        analysis[seed_name] = {
            'phonetic': {
                'current': phonetic_counts,
                'target': phonetic_targets,
                'variations': []
            },
            'orthographic': {
                'current': orthographic_counts,
                'target': orthographic_targets,
                'variations': []
            }
        }
        
        # Show detailed analysis
        print(f"  Phonetic distribution:")
        print(f"    Light: {phonetic_counts['light']}/{phonetic_targets['light']}")
        print(f"    Medium: {phonetic_counts['medium']}/{phonetic_targets['medium']}")
        print(f"    Far: {phonetic_counts['far']}/{phonetic_targets['far']}")
        
        print(f"  Orthographic distribution:")
        print(f"    Light: {orthographic_counts['light']}/{orthographic_targets['light']}")
        print(f"    Medium: {orthographic_counts['medium']}/{orthographic_targets['medium']}")
        print(f"    Far: {orthographic_counts['far']}/{orthographic_targets['far']}")
        
        # Show individual variation scores
        print(f"  Individual variations:")
        for variation in variations:
            p_score = calculate_phonetic_similarity(seed_name, variation)
            o_score = calculate_orthographic_similarity(seed_name, variation)
            print(f"    {variation}: p={p_score:.3f}, o={o_score:.3f}")
    
    return analysis

def test_modify_variations():
    """Test function to demonstrate variation modification."""
    config = {
        "variation_per_seed_name": 8,
        "phonetic_similarity_distribution": {
            "light": {"percentage": 33, "number": 3},
            "medium": {"percentage": 34, "number": 3},
            "far": {"percentage": 33, "number": 3}
        },
        "orthographic_similarity_distribution": {
            "light": {"percentage": 50, "number": 4},
            "medium": {"percentage": 50, "number": 4},
            "far": {"percentage": 0, "number": 0}
        },
        "rule_transformation": {
            "Remove all spaces": {
                "percentage": 10,
                "number": 1,
                "label": "remove_all_spaces"
            },
            "selected_rules": ["remove_all_spaces"]
        }
    }
    
    original_name = "David Johnson"
    existing_variations = ["David", "Dave", "Dav", "Johnson", "Jonson", "John"]
    
    print(f"Original name: {original_name}")
    print(f"Existing variations: {existing_variations}")
    print(f"Config: {config}")
    print("-" * 50)
    
    modified_variations = modify_variations_to_match_config(
        original_name, existing_variations, config
    )
    
    print(f"Modified variations: {modified_variations}")
    
    # Show similarity scores
    print("\nSimilarity Analysis:")
    for variation in modified_variations:
        phonetic_score = calculate_phonetic_similarity(original_name, variation)
        orthographic_score = calculate_orthographic_similarity(original_name, variation)
        print(f"  {variation}: phonetic={phonetic_score:.3f}, orthographic={orthographic_score:.3f}")

def test_with_real_data():
    """Test function with your actual variation result data."""
    
    # Your configuration
    config = {
        "variation_per_seed_name": 8,
        "phonetic_similarity_distribution": {
            "light": {"percentage": 33, "number": 3},
            "medium": {"percentage": 34, "number": 3},
            "far": {"percentage": 33, "number": 3}
        },
        "orthographic_similarity_distribution": {
            "light": {"percentage": 50, "number": 4},
            "medium": {"percentage": 50, "number": 4},
            "far": {"percentage": 0, "number": 0}
        },
        "rule_transformation": {
            "Remove all spaces": {
                "percentage": 10,
                "number": 1,
                "label": "remove_all_spaces"
            },
            "selected_rules": ["remove_all_spaces"]
        }
    }
    
    # Your variation result data
    variation_result = {
        "duane": [
            "Duayne", "Dwain", "Dwane", "Douane", "Dwaneh", "Duayn", "Duwan", "duane"
        ],
        "ashley": [
            "Ashlee", "Ashly", "Ashlei", "Ashely", "Aashley", "Aschley", "Eshley", "ashley"
        ],
        "jessica welch": [
            "Jessika Welch", "Jesica Welch", "Jessyca Welch", "Jesseca Welch", 
            "Jessika Welch", "Jezzica Welch", "Jessyka Welch", "jessicawelch"
        ],
        "david johnson": [
            "David Jonson", "Davyd Johnson", "Daveed Johnson", "Daved Johnson", 
            "Davide Johnston", "Davyd Jonson", "Davit Johnson", "davidjohnson"
        ],
        "jessica": [
            "Jessika", "Jesica", "Jesseca", "Jessyca", "Jezzica", "Jessyla", "Jessice", "jessica"
        ],
        "eric donovan": [
            "Eryk Donovan", "Erik Donovan", "Eric Donavon", "Eric Donoven", 
            "Erick Donovan", "Eric Donivan", "Erec Donovan", "ericdonovan"
        ],
        "megan bowman": [
            "Megan Bowmon", "Mega Bowmane", "Magen Bowman", "Meghan Bowman", 
            "Magen Bowmen", "Meghan Bowmon", "Megane Bowman", "meganbowman"
        ],
        "robert": [
            "Roberd", "Robart", "Robird", "Rohbert", "Robet", "Robett", "Roburt", "robert"
        ],
        "joseph": [
            "Josef", "Josuph", "Jozef", "Josph", "Jossep", "Josaph", "Jociph", "joseph"
        ],
        "april": [
            "Aprel", "Apryl", "Aprel", "Aprille", "Apriil", "Afril", "Apriel", "april"
        ],
        "james watson": [
            "Jaymes Watson", "Jaims Watson", "James Watsin", "James Watcen", 
            "James Watsun", "Jaimes Watson", "Jemes Watson", "jameswatson"
        ],
        "christian": [
            "Kristian", "Cristian", "Christien", "Christan", "Chrustian", "Krystian", "Christin", "christian"
        ],
        "eric lee": [
            "Eric Lea", "Erick Lee", "Erec Lee", "Eryk Lee", "Erick Lea", "Erik Lee", "Eric Leia", "ericlee"
        ],
        "luis contreras": [
            "Luis Contreris", "Luis Contrerasz", "Luis Contreraso", "Lewis Contreras", 
            "Luis Kontreas", "Luis Contraras", "Luiz Contreras", "luiscontreras"
        ],
        "nicholas vega": [
            "Nicholes Vega", "Nicholas Vegaa", "Nickolas Vega", "Nicholas Vegga", 
            "Nicholas Vegha", "Nicholos Vega", "Nicholas Veyga", "nicholasvega"
        ]
    }
    
    print("=" * 60)
    print("ANALYZING CURRENT VARIATION DISTRIBUTION")
    print("=" * 60)
    
    # Analyze current distribution
    analysis = analyze_variation_distribution(variation_result, config)
    
    print("\n" + "=" * 60)
    print("MODIFYING VARIATIONS TO MATCH CONFIG")
    print("=" * 60)
    
    # Modify variations to match config
    modified_result = modify_variation_result_to_match_config(variation_result, config)
    
    print("\n" + "=" * 60)
    print("FINAL MODIFIED VARIATION RESULT")
    print("=" * 60)
    
    # Show final result
    for seed_name, variations in modified_result.items():
        print(f"\n{seed_name}:")
        for i, variation in enumerate(variations, 1):
            p_score = calculate_phonetic_similarity(seed_name, variation)
            o_score = calculate_orthographic_similarity(seed_name, variation)
            print(f"  {i}. {variation} (p={p_score:.3f}, o={o_score:.3f})")
    
    return modified_result

if __name__ == "__main__":
    test_modify_variations()
    test_with_real_data()
