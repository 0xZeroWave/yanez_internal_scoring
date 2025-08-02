import json
import random
import re
from typing import Dict, List, Any
import numpy as np
import os

def calculate_variation_scores(data: dict, variation_config: dict) -> dict:
        """
        Calculate scores for name variations and filter based on quality.
        
        Args:
            data: Dictionary of names and their variations
            
        Returns:
            Filtered dictionary containing only valid variations with good scores
        """
        from app.utils.reward import calculate_variation_quality
        filtered_data = {}
        scores_data = {}
        final_scores = []

        # Validate input structure
        if not isinstance(data, dict) or not data:
            raise ValueError("Invalid or empty data structure")

        # Process each name and variations
        for name, variations in data.items():
            if not name or not isinstance(name, str):
                print(f"Skipping invalid name: {name}")
                continue

            if variations is None or not isinstance(variations, (list, str)):
                print(f"Skipping invalid variations for name: {name}")
                continue

            # Convert single string variation to list
            if isinstance(variations, str):
                variations = [variations]

            if variations:
                try:
                    # Get similarity configurations
                    phonetic_similarity = {
                        k.capitalize(): v['percentage'] 
                        for k, v in variation_config['phonetic_similarity_distribution'].items()
                    }
                    orthographic_similarity = {
                        k.capitalize(): v['percentage'] 
                        for k, v in variation_config['orthographic_similarity_distribution'].items()
                    }

                    # Calculate quality metrics
                    final_score, metrics = calculate_variation_quality(
                        name,
                        variations,
                        phonetic_similarity,
                        orthographic_similarity,
                        variation_config['variation_per_seed_name'],
                        variation_config['rule_transformation']
                    )

                    if final_score > 0.0 and metrics:
                        filtered_data[name] = variations
                        scores_data[name] = metrics
                        final_scores.append(final_score)
                        similarity = metrics.get('first_name', {}).get('metrics', {}).get('similarity', 0.0)

                        # Log metrics
                        print(f"\nScoring results for '{name}':")
                        print(f"Phonetic Similarity: {similarity.get('phonetic', 0.0):.3f}")
                        print(f"Orthographic Similarity: {similarity.get('orthographic', 0.0):.3f}")
                        print(f"Combined Similarity: {similarity.get('combined', 0.0):.3f}")
                        print(f"Final Score: {metrics.get('final_score', 0):.3f}")
                        print(f"Variation Count: {metrics.get('variation_count', 0)}")
                        print(f"Base Score: {metrics.get('base_score', 0):.3f}")
                        print(f"Rule Compliance Score: {metrics.get('rule_compliance', {}).get('score', 0):.3f}")
                        print("===============================================")

                except Exception as e:
                    print(f"Error calculating scores for {name}: {str(e)}")
                    continue
        avg_final_score = np.mean(final_scores) if final_scores else 0.0
        print(f"Average final score across all names: {avg_final_score}")
        return {
            "scores_data": scores_data,
            "final_scores": final_scores,
            "average_final_score": np.mean(final_scores) if final_scores else 0.0
        }