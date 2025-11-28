import asyncio
import json
import requests
import time
from typing import List, Dict, Any

# Test Data - 10 Hinglish Transcripts
TEST_TRANSCRIPTS = [
    {
        "id": 1,
        "stage": "Pre-Due",
        "transcript": "Agent: Hello, main Maya bol rahi hoon, Apex Finance se. Kya main Mr. Sharma se baat kar sakti hoon? Customer: Haan, main bol raha hoon. Kya hua? Agent: Sir, aapka personal loan ka EMI due date 3rd of next month hai. Just calling for a friendly reminder. Aapka payment ready hai na? Customer: Oh, okay. Haan, salary aa jayegi tab tak. I will definitely pay it on time, don't worry. Agent: Thank you, sir. Payment time pe ho jaye toh aapka credit score bhi maintain rahega. Have a good day!",
        "expected_intent": "Payment Reminder Response",
        "expected_sentiment": "Positive",
        "expected_action_required": False
    },
    {
        "id": 2,
        "stage": "Pre-Due",
        "transcript": "Agent: Namaste. Main Priyanka, City Bank credit card department se. Aapka minimum due ₹8,500 hai, jo 10th ko due ho raha hai. Customer: Ji, pata hai. I think main poora amount nahi de paunga, but minimum toh kar dunga. Agent: Sir, pura payment karna best hai, par minimum due must hai to avoid late fees. Koi issue toh nahi hai payment mein? Customer: Nahi, no issue. I'll clear it by the 8th. Agent: Great! Thank you for the confirmation.",
        "expected_intent": "Partial Payment Commitment",
        "expected_sentiment": "Neutral",
        "expected_action_required": True
    },
    {
        "id": 3,
        "stage": "Post-Due (D+7)",
        "transcript": "Agent: Hello Mr. Verma, main Aman bol raha hoon. Aapka personal loan EMI 7 days se overdue hai. Aapne payment kyun nahi kiya? Customer: Dekhiye, thoda emergency aa gaya tha. Mera bonus expected hai next week. Agent: Sir, aapko pata hai ki is par penalty lag rahi hai. Aap exact date bataiye, kab tak confirm payment ho jayega? Customer: Wednesday ko pakka kar dunga. Promise to Pay (PTP) le lo Wednesday ka. Agent: Okay, main aapka PTP book kar raha hoon next Wednesday ke liye. Please ensure payment is done to stop further charges.",
        "expected_intent": "Promise to Pay (PTP)",
        "expected_sentiment": "Neutral",
        "expected_action_required": True
    },
    {
        "id": 4,
        "stage": "Post-Due (D+15)",
        "transcript": "Agent: Good afternoon, Ms. Jain. Aapke credit card ka minimum due 15 din se pending hai. Customer: Oh, I forgot completely. Office mein kaam zyada tha. Agent: Ma'am, aapka total outstanding ab ₹45,000 ho gaya hai, including late fees. Aap aaj hi ₹8,500 ka minimum payment immediate kar dijiye. Customer: Aaj toh nahi ho payega. Sunday ko final karungi. Agent: Sunday is fine, ma'am, but late fees apply ho chuki hain. Please make sure.",
        "expected_intent": "Payment Delay Request",
        "expected_sentiment": "Neutral",
        "expected_action_required": True
    },
    {
        "id": 5,
        "stage": "Post-Due (D+25)",
        "transcript": "Agent: Mr. Khan, aapka loan account N-P-A hone ke risk par hai. 25 days ho gaye hain. Ye serious matter hai. Customer: Main out of station hoon, server issue hai mere bank mein. Agent: Sir, aap online transfer kar sakte hain, ya phir family member se karwa dijiye. Account status kharab ho raha hai. Customer: Thik hai, thik hai. Main next 3 hours mein try karta hoon. Agent: Sir, try nahi, I need a guarantee. Kya main 3 hours mein confirmation call karun? Customer: Haan, call kar lo.",
        "expected_intent": "Technical Issue & Commitment",
        "expected_sentiment": "Negative",
        "expected_action_required": True
    },
    {
        "id": 6,
        "stage": "Recovery (D+60)",
        "transcript": "Agent: Mr. Reddy, main Legal Department se baat kar raha hoon. Aapka loan 60 days se default mein hai. Humari team aapki location par visit karne ki planning kar rahi hai. Customer: Please, visit mat bhejo. Meri job chali gayi hai. I need time! Agent: Sir, time humne bahut diya hai. Aap kitna amount abhi immediately de sakte hain? Customer: Abhi main only ₹10,000 de sakta hoon. Baaki next month. Agent: Okay, ₹10,000 ka token payment kar dijiye. Hum aapki file temporary hold par rakhenge.",
        "expected_intent": "Financial Hardship & Token Payment",
        "expected_sentiment": "Negative",
        "expected_action_required": True
    },
    {
        "id": 7,
        "stage": "Recovery (D+90)",
        "transcript": "Agent: Ma'am, aapka account write-off hone ki verge par hai. 90 days ho gaye hain. Aapka total due ₹1.5 lakh hai. Customer: Main itna paisa nahi de sakti. Please settlement option do. Agent: Settlement ke liye aapko pehle minimum 30% upfront dena hoga. Kya aap eligible hain? Customer: Mujhe details mail kar do. Main check karti hoon. Agent: Main aapko final warning de raha hoon. Agar aapne action nahi liya toh legal notice jayega.",
        "expected_intent": "Settlement Request",
        "expected_sentiment": "Negative",
        "expected_action_required": True
    },
    {
        "id": 8,
        "stage": "Recovery (D+120)",
        "transcript": "Agent: Mr. Singh, aapka case external agency ko assign ho chuka hai. Hum final discussion ke liye call kar rahe hain. Aapki property par charge hai. Customer: No, no, personal loan par koi charge nahi hai. Stop threatening! Agent: Sir, as per the loan agreement, hum action le sakte hain. Aap aaj ₹25,000 transfer kijiye for account regularization. Customer: I'll talk to my lawyer. Agent: That's your right, sir, but payment is mandatory.",
        "expected_intent": "Legal Threat Dispute",
        "expected_sentiment": "Negative",
        "expected_action_required": True
    },
    {
        "id": 9,
        "stage": "Recovery (D+60, Dispute)",
        "transcript": "Agent: Hello, Mr. Kumar. 60 days outstanding. What is the payment plan? Customer: Maine aapko pehle hi bataya tha, ek transaction fraud tha. Jab tak woh resolve nahi hoga, main payment nahi karunga. Agent: Sir, dispute department separate hai. Aapka due amount legal hai. You must pay the undisputed amount first. Customer: No, first resolve the dispute! Agent: Sir, both processes run parallel. Please pay the minimum due today.",
        "expected_intent": "Fraud Dispute Claim",
        "expected_sentiment": "Negative",
        "expected_action_required": True
    },
    {
        "id": 10,
        "stage": "Recovery (D+75, Hardship)",
        "transcript": "Agent: Ms. Pooja, hum aapko 75 days se call kar rahe hain. Aap cooperate nahi kar rahe. Customer: Meri mother hospital mein hain. Serious financial hardship hai. I am requesting a restructuring of the loan. Agent: Ma'am, we understand the situation. Lekin restructuring ke liye aapko hardship application fill karni hogi aur last 3 months ka bank statement dena hoga. Customer: Okay, send me the form.",
        "expected_intent": "Hardship & Restructuring Request",
        "expected_sentiment": "Neutral",
        "expected_action_required": True
    }
]

class PipelineValidator:
    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url
        self.results = []
    
    def test_api_connection(self) -> bool:
        """Test if the API is running and accessible"""
        try:
            response = requests.get(f"{self.api_url}/docs")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """Send transcript to API and get insights"""
        try:
            payload = {"transcript": transcript}
            response = requests.post(
                f"{self.api_url}/analyze_call",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def evaluate_result(self, expected: Dict, actual: Dict) -> Dict[str, Any]:
        """Compare expected vs actual results"""
        if "error" in actual:
            return {
                "intent_match": False,
                "sentiment_match": False,
                "action_match": False,
                "error": actual["error"]
            }
        
        insights = actual.get("insights", {})
        
        # Extract actual values
        actual_intent = insights.get("customer_intent", "")
        actual_sentiment = insights.get("sentiment", "")
        actual_action = insights.get("action_required", False)
        
        # Simple keyword-based matching for intent (more flexible)
        intent_keywords = expected["expected_intent"].lower().split()
        intent_match = any(keyword in actual_intent.lower() for keyword in intent_keywords)
        
        # Exact match for sentiment and action
        sentiment_match = actual_sentiment == expected["expected_sentiment"]
        action_match = actual_action == expected["expected_action_required"]
        
        return {
            "intent_match": intent_match,
            "sentiment_match": sentiment_match,
            "action_match": action_match,
            "actual_intent": actual_intent,
            "actual_sentiment": actual_sentiment,
            "actual_action": actual_action,
            "expected_intent": expected["expected_intent"],
            "expected_sentiment": expected["expected_sentiment"],
            "expected_action": expected["expected_action_required"]
        }
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and compile results"""
        print("🚀 Starting Conversational Insights Pipeline Validation")
        print("=" * 60)
        
        # Check API connection
        if not self.test_api_connection():
            print("❌ ERROR: API is not accessible. Make sure uvicorn server is running.")
            print("Run: uvicorn main:app --reload")
            return {"error": "API not accessible"}
        
        print("✅ API connection successful")
        print("\n📊 Processing transcripts...\n")
        
        # Process each transcript
        for i, test_case in enumerate(TEST_TRANSCRIPTS, 1):
            print(f"Test {i}/10: {test_case['stage']} (ID: {test_case['id']})")
            
            # Analyze transcript
            result = self.analyze_transcript(test_case['transcript'])
            
            # Evaluate result
            evaluation = self.evaluate_result(test_case, result)
            
            # Store result
            self.results.append({
                "test_id": test_case['id'],
                "stage": test_case['stage'],
                "evaluation": evaluation,
                "raw_result": result
            })
            
            # Print immediate feedback
            if "error" in evaluation:
                print(f"   ❌ ERROR: {evaluation['error']}")
            else:
                intent_status = "✅" if evaluation['intent_match'] else "❌"
                sentiment_status = "✅" if evaluation['sentiment_match'] else "❌"
                action_status = "✅" if evaluation['action_match'] else "❌"
                
                print(f"   Intent: {intent_status} | Sentiment: {sentiment_status} | Action: {action_status}")
            
            # Rate limiting
            time.sleep(1)
        
        # Compile summary
        return self.compile_summary()
    
    def compile_summary(self) -> Dict[str, Any]:
        """Compile test results summary"""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if "error" not in r['evaluation'])
        
        if successful_tests == 0:
            return {
                "summary": {
                    "total_tests": total_tests,
                    "successful_tests": 0,
                    "failed_tests": total_tests,
                    "success_rate": 0.0
                },
                "details": self.results
            }
        
        # Calculate accuracy metrics
        intent_accuracy = sum(1 for r in self.results 
                             if r['evaluation'].get('intent_match', False)) / successful_tests * 100
        sentiment_accuracy = sum(1 for r in self.results 
                                if r['evaluation'].get('sentiment_match', False)) / successful_tests * 100
        action_accuracy = sum(1 for r in self.results 
                             if r['evaluation'].get('action_match', False)) / successful_tests * 100
        
        # Stage-wise analysis
        stage_analysis = {}
        for result in self.results:
            stage = result['stage']
            if stage not in stage_analysis:
                stage_analysis[stage] = {'total': 0, 'successful': 0}
            
            stage_analysis[stage]['total'] += 1
            if "error" not in result['evaluation']:
                stage_analysis[stage]['successful'] += 1
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": (successful_tests / total_tests) * 100,
                "intent_accuracy": intent_accuracy,
                "sentiment_accuracy": sentiment_accuracy,
                "action_accuracy": action_accuracy
            },
            "stage_analysis": stage_analysis,
            "details": self.results
        }
    
    def print_detailed_report(self, summary: Dict[str, Any]):
        """Print comprehensive test report"""
        print("\n" + "=" * 60)
        print("📈 PIPELINE VALIDATION REPORT")
        print("=" * 60)
        
        # Overall Summary
        summary_data = summary['summary']
        print(f"Total Tests: {summary_data['total_tests']}")
        print(f"Successful: {summary_data['successful_tests']}")
        print(f"Failed: {summary_data['failed_tests']}")
        print(f"Success Rate: {summary_data['success_rate']:.1f}%")
        
        if summary_data['successful_tests'] > 0:
            print(f"\nAccuracy Metrics:")
            print(f"Intent Recognition: {summary_data['intent_accuracy']:.1f}%")
            print(f"Sentiment Analysis: {summary_data['sentiment_accuracy']:.1f}%")
            print(f"Action Detection: {summary_data['action_accuracy']:.1f}%")
        
        # Stage-wise Analysis
        if 'stage_analysis' in summary:
            print(f"\n📊 Stage-wise Performance:")
            for stage, data in summary['stage_analysis'].items():
                success_rate = (data['successful'] / data['total']) * 100
                print(f"  {stage}: {data['successful']}/{data['total']} ({success_rate:.1f}%)")
        
        # Detailed Results
        print(f"\n🔍 Detailed Results:")
        for result in summary['details']:
            print(f"\nTest {result['test_id']} - {result['stage']}:")
            evaluation = result['evaluation']
            
            if 'error' in evaluation:
                print(f"  ❌ Error: {evaluation['error']}")
            else:
                print(f"  Intent: {'✅' if evaluation['intent_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_intent']}, Got: {evaluation['actual_intent']})")
                print(f"  Sentiment: {'✅' if evaluation['sentiment_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_sentiment']}, Got: {evaluation['actual_sentiment']})")
                print(f"  Action: {'✅' if evaluation['action_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_action']}, Got: {evaluation['actual_action']})")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if summary_data['success_rate'] < 80:
            print("  - Consider improving LLM prompt engineering")
            print("  - Add more context-specific examples in prompts")
        
        if summary_data.get('intent_accuracy', 0) < 70:
            print("  - Enhance intent recognition with domain-specific keywords")
        
        if summary_data.get('sentiment_accuracy', 0) < 80:
            print("  - Fine-tune sentiment analysis for Hinglish expressions")
        
        if summary_data.get('action_accuracy', 0) < 85:
            print("  - Clarify action_required logic in business rules")


def main():
    """Main execution function"""
    print("Conversational Insights Pipeline - Hinglish Transcripts Validation")
    print("Please ensure your FastAPI server is running: uvicorn main:app --reload")
    input("Press Enter to start testing...")
    
    validator = PipelineValidator()
    summary = validator.run_comprehensive_test()
    
    if "error" in summary:
        print(f"❌ Test execution failed: {summary['error']}")
        return
    
    validator.print_detailed_report(summary)
    
    # Save results to file
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to 'test_results.json'")


if __name__ == "__main__":
    main()