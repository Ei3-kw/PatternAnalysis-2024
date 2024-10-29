"""
This module is used to show example usage the trained ViT model by using the model to predict
on a testing set from the ADNI brain dataset

Evaluation metrics will be printed and evaluation figures will be saved to the current folder.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from tqdm import tqdm
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

from dataset import get_dataset
from modules import ViTClassifier

def load_trained_model(model_path, device):
    """
    Load a trained model from checkpoint
    """
    # Initialize model architecture
    model = ViTClassifier(num_classes=4).to(device)

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device)

    # Handle different checkpoint formats
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)

    return model

def evaluate_model(model, test_loader, device, classes):
    """
    Evaluate model performance on test set
    """
    model.eval()

    # Initialize lists to store predictions and true labels
    all_preds = []
    all_labels = []
    all_probs = []

    # Testing loop
    with torch.no_grad():
        for images, labels in tqdm(test_loader, desc="Evaluating"):
            images = images.to(device)
            outputs = model(images)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs.data, 1)

            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probabilities.cpu().numpy())

    return np.array(all_preds), np.array(all_labels), np.array(all_probs)

def plot_confusion_matrix(y_true, y_pred, classes, save_path):
    """
    Plot and save confusion matrix
    """
    # Get unique classes actually present in the data
    present_classes = np.unique(np.concatenate([y_true, y_pred]))
    present_class_names = [classes[i] for i in present_classes]

    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=present_class_names,
                yticklabels=present_class_names)
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(save_path / 'confusion_matrix.png')
    plt.close()

    # Calculate per-class accuracy
    per_class_accuracy = cm.diagonal() / cm.sum(axis=1)
    return per_class_accuracy, present_class_names

def evaluate_model(model, test_loader, device, classes):
    """
    Evaluate model performance on test set
    """
    model.eval()

    # Initialize lists to store predictions and true labels
    all_preds = []
    all_labels = []
    all_probs = []

    # Testing loop
    with torch.no_grad():
        for images, labels in tqdm(test_loader, desc="Evaluating"):
            images = images.to(device)
            outputs = model(images)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs.data, 1)

            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probabilities.cpu().numpy())

    return np.array(all_preds), np.array(all_labels), np.array(all_probs)

def main():
    # Configuration
    BATCH_SIZE = 32
    CLASSES = ['CN', 'MCI', 'AD', 'SMC']
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # Create results directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_dir = Path(f'evaluation_results_{timestamp}')
    results_dir.mkdir(exist_ok=True)

    print(f"\nEvaluation Results will be saved to: {results_dir}")

    # Load test dataset
    print("\nLoading test dataset...")
    test_dataset = get_dataset(train=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=4)
    print(f"Test set size: {len(test_dataset)} images")

    # Load model
    model_path = "./checkpoints/best_model_20241029_170413.pt"
    print(f"Loading model from {model_path}...")
    model = load_trained_model(model_path, device)
    model.eval()

    # Evaluate model
    print("\nEvaluating model...")
    predictions, true_labels, probabilities = evaluate_model(model, test_loader, device, CLASSES)

    # Get unique classes present in the data
    present_classes = np.unique(true_labels)
    present_class_names = [CLASSES[i] for i in present_classes]

    print("\nCalculating metrics...")

    # Classification report with only present classes
    report = classification_report(
        true_labels,
        predictions,
        labels=present_classes,
        target_names=present_class_names,
        output_dict=True
    )

    # Per-class accuracy from confusion matrix
    per_class_accuracy, matrix_classes = plot_confusion_matrix(
        true_labels, predictions, CLASSES, results_dir
    )

    # Plot ROC curves only for present classes
    if len(present_classes) > 1:  # Only plot ROC curves if there are multiple classes
        plot_roc_curves(true_labels, probabilities[:, present_classes],
                       present_class_names, results_dir)

    # Compile metrics
    metrics = {
        'classification_report': report,
        'per_class_accuracy': {
            class_name: acc for class_name, acc in zip(matrix_classes, per_class_accuracy)
        },
        'overall_accuracy': (predictions == true_labels).mean(),
        'model_path': model_path,
        'evaluation_date': timestamp,
        'test_set_size': len(test_dataset),
        'classes_present': present_class_names
    }

    # Save metrics
    save_metrics(metrics, results_dir)

    # Print summary
    print("\nEvaluation Results Summary:")
    print(f"Classes present in test set: {', '.join(present_class_names)}")
    print(f"Overall Accuracy: {metrics['overall_accuracy']*100:.2f}%")
    print("\nPer-class Accuracy:")
    for class_name, acc in metrics['per_class_accuracy'].items():
        print(f"{class_name}: {acc*100:.2f}%")

    print(f"\nDetailed results have been saved to {results_dir}")
    print("Files generated:")
    print("- confusion_matrix.png")
    if len(present_classes) > 1:
        print("- roc_curves.png")
    print("- evaluation_metrics.json")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        raise